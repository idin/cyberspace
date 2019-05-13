from bs4 import BeautifulSoup
import re
import warnings
from pensieve import Pensieve
from slytherin.collections import flatten, remove_list_duplicates
from slytherin.collections import remove_list_duplicates, flatten
from interaction import ProgressBar
from abstract import Graph
from interaction import iterate

from .exceptions import PageError, RedirectError, ODD_ERROR_MESSAGE
from .InfoBox import InfoBox
from .get_wikipedia_id import get_wikipedia_id
from ...beautiful_soup_helpers import get_lists, find_links, clone_beautiful_soup_tag, parse_link


class Page:
	def __init__(self, api=None, id=None, url=None, title=None, namespace=None, redirect=True, disambiguation_url=None):
		self._api = api
		self._pensieve = Pensieve(safe=False, function_durations=self.api.function_durations)
		if id or title or url:
			pass
		else:
			raise ValueError('Either id or title or url should be given!')

		self._pensieve['namespace'] = namespace
		self._pensieve['redirect'] = redirect
		self._pensieve['disambiguation_url'] = disambiguation_url

		if id:
			self._pensieve['original_id'] = id
			self._load_from_id()

		elif url:
			self._pensieve['url'] = url
			self._load_from_url()

		elif title:
			self._pensieve['original_title'] = title
			self._load_from_title()
		self._load_the_rest()

	@staticmethod
	def _get_disambiguation_results(disambiguation, parsed_html, base_url):
		if disambiguation:
			original_content = parsed_html.find(attrs={'id': 'bodyContent'}).find(attrs={'id': 'mw-content-text'})
			content = clone_beautiful_soup_tag(element=original_content)
			disambigbox = content.find(attrs={'id': 'disambigbox'})
			if disambigbox:
				disambigbox.extract()
			printfooter = content.find(attrs={'class': 'printfooter'})
			if printfooter:
				printfooter.extract()
			links = find_links(element=content, base=base_url)
			return [link for link in links if '/index.php?' not in link['url']]
		else:
			return []

	def _parse_search_results(self):
		for key in ['id', 'title', 'page', 'redirected_from', 'language', 'namespace', 'full_url', 'disambiguation']:
			self._pensieve.store(key, precursors=['search_result'], function=lambda x: x[key])

		self._pensieve.store(
			key='json', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_json(id=x['id'], title=x['title'])
		)

	def _get_url_response(self):
		self._pensieve.store(
			key='url_response', precursors=['url'], evaluate=False,
			function=lambda x: self.request(url=x, format='response')
		)

	def _load_from_url(self):
		self._get_url_response()

		self._pensieve.store(
			key='original_id', precursors=['url_response'], evaluate=False,
			function=lambda x: get_wikipedia_id(x.text)
		)
		self._pensieve.store(
			key='search_result', precursors=['original_id', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=None, id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)
		self._parse_search_results()

	def _load_from_id(self):
		self._pensieve.store(
			key='search_result', precursors=['original_id', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=None, id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)
		self._parse_search_results()
		self._pensieve.store(key='url', precursors=['page'], function=lambda x: x['fullurl'], evaluate=False)
		self._get_url_response()

	def _load_from_title(self):
		self._pensieve.store(
			key='search_result', precursors=['original_title', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=x['original_title'], id=None, redirect=x['redirect'],
				redirected_from=None
			)
		)
		self._parse_search_results()
		self._pensieve.store(key='url', precursors=['page'], function=lambda x: x['fullurl'], evaluate=False)
		self._get_url_response()

	def get_children(self, echo=1):
		link_lists = self['link_list']
		if link_lists:
			urls = remove_list_duplicates([link['url'] for link in flatten(link_lists)])
			wikipedia_urls = [url for url in urls if re.match('^https://.+\.wikipedia.org/', url)]
			non_php_urls = [url for url in wikipedia_urls if '/index.php?' not in url]

			pages = ProgressBar.map(
				function=lambda x: self.__class__(url=x, redirect=self['redirect'], api=self.api),
				iterable=non_php_urls, echo=echo, text=self['url']
			)
			return pages
		else:
			return []

	def _load_the_rest(self):
		self._pensieve.store(
			key='base_url', precursors=['url'], evaluate=False, materialize=False,
			function=lambda x: x[:x.find('/wiki/')]
		)

		self._pensieve.store(
			key='parsed_html', precursors=['url_response'], evaluate=False,
			function=lambda x: BeautifulSoup(x.text, 'lxml')
		)

		self._pensieve.store(
			key='disambiguation_results',
			precursors=['disambiguation', 'parsed_html', 'base_url'],
			evaluate=False,
			function=lambda x: self._get_disambiguation_results(
				disambiguation=x['disambiguation'], parsed_html=x['parsed_html'], base_url=x['base_url']
			)
		)

		def _get_anchors_and_links(parsed_html, base_url):
			result = {}
			for l in parsed_html.find_all(name='ul'):
				for link in find_links(element=l, base=base_url):
					if link['url'] not in result:
						result[link['url']] = link
			return list(result.values())

		self._pensieve.store(
			key='link_and_anchor_list', precursors=['parsed_html', 'base_url'], evaluate=False,
			function=lambda x: _get_anchors_and_links(parsed_html=x['parsed_html'], base_url=x['base_url'])
		)

		self._pensieve.store(
			key='nested_link_and_anchor_lists', precursors=['parsed_html', 'base_url'], evaluate=False,
			function=lambda x: get_lists(element=x['parsed_html'], links_only=True, base=x['base_url'])
		)

		#	ANCHORS IN A PAGE
		def _remove_nonanchors(link_lists):
			if isinstance(link_lists, list):
				result = [_remove_nonanchors(ll) for ll in link_lists if ll]
				result = [x for x in result if x is not None]
				result = [x for x in result if len(x) > 0 or not isinstance(x, list)]
				if len(result) > 1:
					return result
				elif len(result) == 1:
					return result[0]
				else:
					return None
			elif isinstance(link_lists, dict):
				if not link_lists['url'].startswith('#'):
					return None
				else:
					return link_lists

		self._pensieve.store(
			key='nested_anchor_lists', precursors=['nested_link_and_anchor_lists'], evaluate=False,
			function=_remove_nonanchors
		)

		self._pensieve.store(
			key='anchor_list', precursors=['link_and_anchor_list'], evaluate=False,
			function=_remove_nonanchors
		)

		# 	LINKS IN A PAGE
		def _remove_anchors(link_lists):
			if isinstance(link_lists, list):
				result = [_remove_anchors(ll) for ll in link_lists if ll]
				result = [x for x in result if x is not None]
				result = [x for x in result if len(x)>0 or not isinstance(x, list)]
				if len(result) > 1:
					return result
				elif len(result) == 1:
					return result[0]
				else:
					return None
			elif isinstance(link_lists, dict):
				if 'url' not in link_lists:
					print(link_lists)
				if link_lists['url'].startswith('#'):
					return None
				else:
					return link_lists

		self._pensieve.store(
			key='nested_link_lists', precursors=['nested_link_and_anchor_lists'], evaluate=False,
			function=_remove_anchors
		)

		self._pensieve.store(
			key='link_list', precursors=['link_and_anchor_list'], evaluate=False,
			function=_remove_anchors
		)

		self._pensieve.store(
			key='summary', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_summary(id=x['id'], title=x['title'])
		)

		self._pensieve.store(
			key='content', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_content(id=x['id'], title=x['title'])
		)

		self._pensieve.store(
			key='extract', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['extract']
		)

		self._pensieve.store(
			key='revision_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['revid']
		)

		self._pensieve.store(
			key='parent_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['parentid']
		)

		self._pensieve.store(
			key='info_box', precursors=['url_response'], evaluate=False, materialize=True,
			function=lambda x: InfoBox(html=x.text)
		)

		# # # Persons:
		'''
		self._pensieve.store(
			key='birthdate', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_date_in_info_box(info_box=x, label='born')
		)

		self._pensieve.store(
			key='deathdate', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_date_in_info_box(info_box=x, label='died')
		)

		self._pensieve.store(
			key='occupation', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_in_info_box(info_box=x, label='occupation')
		)

		# # # Companies

		self._pensieve.store(
			key='ticker', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_in_info_box(info_box=x, label='traded as')[0].text
		)

		self._pensieve.store(
			key='isin', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_links_in_info_box(info_box=x, label='isin')
		)

		self._pensieve.store(
			key='founders', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_links_in_info_box(info_box=x, label='founders')
		)

		self._pensieve.store(
			key='founded', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_date_in_info_box(info_box=x, label='founded')
		)

		self._pensieve.store(
			key='industry', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_links_in_info_box(info_box=x, label='industry')
		)

		self._pensieve.store(
			key='headquarters', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_in_info_box(info_box=x, label='headquarters')[0].text
		)
		'''

	def get_graph(self, max_depth=1, strict=True, ordering=True, echo=1):
		graph = Graph(obj=None, strict=strict, ordering=ordering)
		def _crawl(graph, page, max_depth, parent_page, depth, echo):
			if page['id'] not in graph:
				graph.add_node(name=page['id'], label=page['title'], value=page['url'])
				if depth < max_depth:
					link_lists = page['link_lists']
					if link_lists:
						urls = remove_list_duplicates([link['url'] for link in flatten(link_lists)])
						if link_lists:
							for url in iterate(iterable=urls, echo=echo, text=page['title']):
								if re.match('^https://.+\.wikipedia.org/', url):
									try:
										child_page = Page(api=page.api, url=url)
										_crawl(
											graph=graph, page=child_page, parent_page=page, max_depth=max_depth,
											depth=depth+1, echo=echo
										)
									except KeyError as e:
										warnings.warn(str(e))
			if parent_page:
				graph.connect(start=parent_page['id'], end=page['id'])

		if echo:
			print(self['url'])
		_crawl(graph=graph, page=self, max_depth=max_depth, parent_page=None, depth=0, echo=echo)

		return graph

	@property
	def pensieve(self):
		"""
		:rtype: Pensieve
		"""
		return self._pensieve

	@property
	def base_url(self):
		return 'http://' + self.api.language + '.wikipedia.org'

	def clear(self):
		new_pensieve = Pensieve(safe=True)
		for key in ['original_id', 'original_title', 'namespace', 'redirect', 'redirected_from']:
			new_pensieve[key] = self.pensieve[key]
		self._pensieve = new_pensieve

	@staticmethod
	def _get_state_attributes():
		return ['_pensieve']

	def __getstate__(self):
		return {name: getattr(self, name) for name in self._get_state_attributes()}

	def __setstate__(self, state):
		for name in self._get_state_attributes():
			setattr(self, name, state[name])
		self._api = None

	@property
	def title(self):
		if 'title' in self._pensieve:
			return self._pensieve['title']
		else:
			return self._pensieve['original_title']

	@property
	def id(self):
		if 'id' in self._pensieve:
			return self._pensieve['id']
		else:
			return self._pensieve['original_id']

	@property
	def url(self):
		if 'url' not in self._pensieve:
			raise AttributeError(f'Page {self} does not have a url!')
		elif self._pensieve['url'] is None:
			raise AttributeError(f'Page {self} does not have a url!')
		return self._pensieve['url']

	def __str__(self):
		if 'url' in self._pensieve:
			url = self._pensieve['url']
			return f'{self.title}: {url}'
		else:
			return f'{self.title}: {self.id}'

	def __repr__(self):
		return str(self)

	@property
	def api(self):
		"""
		:rtype: .Wikipedia_class.Wikipedia
		"""
		if self._api is None:
			raise AttributeError('Wikipedia API is missing!')
		else:
			return self._api

	@api.setter
	def api(self, api):
		"""
		:type api: .Wikipedia_class.Wikipedia
		"""
		self._api = api

	def request(self, url=None, parameters=None, format='html'):
		return self.api.request(url=url, parameters=parameters, format=format)

	@staticmethod
	def _get_search_parameters(id, title):
		query_parameters = {
			'prop': 'info|pageprops',
			'inprop': 'url',
			'ppprop': 'disambiguation',
			'redirects': '',
		}

		if id:
			query_parameters['pageids'] = id
		else:
			query_parameters['titles'] = title

		return query_parameters

	@staticmethod
	def _get_html_parameters(id, title):
		query_params = {
			'prop': 'revisions',
			'rvprop': 'content',
			'rvparse': '',
			'rvlimit': 1
		}
		if id:
			query_params['pageids'] = id
		else:
			query_params['titles'] = title
		return query_params

	@staticmethod
	def _get_summary_parameters(id, title):
		query_params = {
			'prop': 'extracts',
			'explaintext': '',
			'exintro': '',
		}
		if id:
			query_params['pageids'] = id
		else:
			query_params['titles'] = title
		return query_params

	@staticmethod
	def _get_content_parameters(id, title):
		query_params = {
			'prop': 'extracts|revisions',
			'explaintext': '',
			'rvprop': 'ids'
		}
		if id:
			query_params['pageids'] = id
		else:
			query_params['titles'] = title

		return query_params

	def _search_page(self, id, title, redirect, redirected_from, num_recursions=0):
		if num_recursions > 3:
			raise RecursionError()
		# print(dict(title=title, id=id, redirect=redirect, redirected_from=redirected_from, num_recursions=num_recursions))

		search_query_parameters = self._get_search_parameters(id=id, title=title)
		search_request = self.request(parameters=search_query_parameters, format='json')

		query = search_request['query']
		id = list(query['pages'].keys())[0]
		page = query['pages'][id]
		title = page['title']
		full_url = page['fullurl']
		language = page['pagelanguage']
		namespace = page['ns']

		# missing is present if the page is missing

		if 'missing' in page:
			raise PageError(id=id, title=title)

		# same thing for redirect, except it shows up in query instead of page for
		# whatever silly reason
		elif 'redirects' in query:
			if redirect:
				redirects = query['redirects'][0]

				if 'normalized' in query:
					normalized = query['normalized'][0]
					assert normalized['from'] == self.title, ODD_ERROR_MESSAGE

					from_title = normalized['to']

				else:
					from_title = self.title

				assert redirects['from'] == from_title, ODD_ERROR_MESSAGE

				# change the title and reload the whole object

				return self._search_page(
					id=id, title=redirects['to'],
					redirect=redirect, redirected_from=redirects['from'],
					num_recursions=num_recursions+1
				)
			else:
				raise RedirectError(getattr(self, 'title', page['title']))

		# since we only asked for disambiguation in ppprop,
		# if a pageprop is returned,
		# then the page must be a disambiguation page
		elif 'pageprops' in page:
			return {
				'id': str(id), 'title': title, 'page': page, 'redirected_from': redirected_from,
				'full_url': full_url, 'language': language, 'namespace': namespace, 'disambiguation': True
			}

		else:
			return {
				'id': str(id), 'title': title, 'page': page, 'redirected_from': redirected_from,
				'full_url': full_url, 'language': language, 'namespace': namespace, 'disambiguation': False
			}

	def _get_json(self, id, title):
		html_query_parameters = self._get_html_parameters(id=id, title=title)
		html_request = self.request(parameters=html_query_parameters, format='json')
		return html_request['query']['pages'][id]['revisions'][0]['*']

	@staticmethod
	def _get_links(parsed_html, base_url):
		links = parsed_html.find_all('a')
		parsed_links = [parse_link(link, base=base_url) for link in links]
		return [link for link in parsed_links if link]

	def _get_summary(self, id, title):
		summary_query_parameters = self._get_summary_parameters(id=id, title=title)
		summary_request = self.request(parameters=summary_query_parameters, format='json')
		return summary_request['query']['pages'][id]['extract']

	def _get_content(self, id, title):
		content_parameters = self._get_content_parameters(id=id, title=title)
		content_request = self.request(parameters=content_parameters, format='json')
		return content_request['query']['pages'][id]





	'''
	@staticmethod
	def _find_in_info_box(info_box, label):
		def __get_th_text(tr):
			try:
				return tr.find('th').text.lower()
			except:
				return ''

		return [tr for tr in info_box.find_all('tr') if label in __get_th_text(tr=tr)]
		
	@classmethod
	def _find_links_in_info_box(cls, info_box, label):
		trs = cls._find_in_info_box(info_box=info_box, label=label)
		return [{'link': link.get('href'), 'text': link.get_text()} for tr in trs for link in tr.find_all('a')]
	
	@classmethod
	def _find_date_in_info_box(cls, info_box, label):
		trs = cls._find_in_info_box(info_box=info_box, label=label)
		dates = [date for tr in trs for date in datefinder.find_dates(tr.text)]
		if len(dates) > 0:
			return dates[0]
		else:
			return None
	'''

	def __getitem__(self, item):
		return self.pensieve[item]

	def __graph__(self):
		return self._pensieve.__graph__()
