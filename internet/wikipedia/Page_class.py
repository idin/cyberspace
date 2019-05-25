from .exceptions import PageError, RedirectError, ODD_ERROR_MESSAGE
from .InfoBox_class import InfoBox
from .get_wikipedia_id import get_wikipedia_id, get_page_title, get_page_language, get_page_namespace
from .Page_helper_functions import *
from .is_wikipedia_page_url_function import is_wikipedia_page_url
from .is_wikipedia_page_url_function import is_mobile_wikipedia_page_url
from .is_wikipedia_page_url_function import convert_mobile_wikipedia_page_url_to_normal_page

from ..beautiful_soup_helpers import get_paragraphs_and_tokens
from ..beautiful_soup_helpers import read_table


import re
from pensieve import Pensieve
from slytherin.collections import remove_list_duplicates, flatten
from ravenclaw.wrangling import standardize_columns
from interaction import ProgressBar
from internet.beautiful_soup_helpers import get_lists, parse_link, find_links
from linguistics import tokenize


class Page:
	def __init__(self, api=None, id=None, url=None, title=None, namespace=None, redirect=True, disambiguation_url=None):
		self._api = api
		self._pensieve = Pensieve(safe=False, function_durations=self.api.function_durations, warn_unsafe=False)
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
			if is_wikipedia_page_url(url=url):
				if is_mobile_wikipedia_page_url(url=url):
					url = convert_mobile_wikipedia_page_url_to_normal_page(url=url)
				self._pensieve['url'] = url
				self._load_from_url()
			else:
				raise ValueError(f'{url} does not match the wikipedia page pattern!')

		elif title:
			self._pensieve['original_title'] = title
			self._load_from_title()
		self._load_the_rest()

	def __getstate__(self):
		return self._pensieve

	def __setstate__(self, state):
		self._pensieve = state
		self._api = None

	def __eq__(self, other):
		"""
		:type other: Page
		:rtype: bool
		"""
		if isinstance(other, self.__class__):
			return self['url'] == other['url']
		else:
			return False

	def __str__(self):
		if 'url' in self._pensieve:
			url = self._pensieve['url']
			return f'{self.title}: {url} '
		else:
			return f'{self.title}: {self.id} '

	def __repr__(self):
		return str(self)

	def __getitem__(self, item):
		return self.pensieve[item]

	def __graph__(self):
		return self._pensieve.__graph__()

	@property
	def title(self):
		"""
		:rtype: str
		"""
		if 'title' in self._pensieve:
			return self._pensieve['title']
		else:
			return self._pensieve['original_title']

	@property
	def id(self):
		"""
		:rtype: int
		"""
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

	@property
	def api(self):
		"""
		:rtype: .Wikipedia_class.Wikipedia
		"""
		if self._api is None:
			raise AttributeError('Wikipedia API is missing!')
		else:
			return self._api

	@property
	def pensieve(self):
		"""
		:rtype: Pensieve
		"""
		return self._pensieve

	@property
	def base_url(self):
		"""
		:rtype: str
		"""
		return 'http://' + self.api.language + '.wikipedia.org'

	@api.setter
	def api(self, api):
		"""
		:type api: .Wikipedia_class.Wikipedia
		"""
		self._api = api

	def get_children(self, echo=1):
		link_lists = self['link_list']
		if link_lists:
			urls = remove_list_duplicates([link.url for link in flatten(link_lists)])
			wikipedia_urls = [url for url in urls if re.match('^https://.+\.wikipedia.org/', url)]
			non_php_urls = [url for url in wikipedia_urls if '/index.php?' not in url]

			pages = ProgressBar.map(
				function=lambda x: self.__class__(url=x, redirect=self['redirect'], api=self.api),
				iterable=non_php_urls, echo=echo, text=self['url']
			)
			return pages
		else:
			return []

	def request(self, url=None, parameters=None, format='html'):
		return self.api.request(url=url, parameters=parameters, format=format)

	def clear(self):
		new_pensieve = Pensieve(safe=True)
		for key in ['original_id', 'original_title', 'namespace', 'redirect', 'redirected_from']:
			new_pensieve[key] = self.pensieve[key]
		self._pensieve = new_pensieve

	def _search_page(self, id, title, redirect, redirected_from, num_recursions=0):
		if num_recursions > 3:
			raise RecursionError()
		# print(dict(title=title, id=id, redirect=redirect, redirected_from=redirected_from, num_recursions=num_recursions))

		search_query_parameters = get_search_parameters(id=id, title=title)
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
				'id':int(id), 'title': title, 'page': page, 'redirected_from': redirected_from,
				'full_url': full_url, 'language': language, 'namespace': namespace, 'disambiguation': True
			}

		else:
			return {
				'id': int(id), 'title': title, 'page': page, 'redirected_from': redirected_from,
				'full_url': full_url, 'language': language, 'namespace': namespace, 'disambiguation': False
			}

	def _parse_search_results(self, keys):

		def create_search_item_function(_key):
			def get_search_item(x):
				return x[_key]
			return get_search_item
		for key in keys:
			self._pensieve.store(
				key, precursors=['search_result'],
				function=create_search_item_function(_key=key),
				evaluate=False
			)

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

		self._pensieve.store(
			key='id', precursors=['url_response'], evaluate=False,
			function=lambda x: get_wikipedia_id(x.text)
		)
		self._pensieve.store(
			key='title', precursors=['url_response'], evaluate=False,
			function=lambda x: get_page_title(x.text)
		)
		self._pensieve.store(
			key='language', precursors=['url_response'], evaluate=False,
			function=lambda x: get_page_language(x.text)
		)
		self._pensieve.store(
			key='namespace', precursors=['url_response'], evaluate=False,
			function=lambda x: get_page_namespace(x.text)
		)
		self._pensieve.store(
			key='full_url', precursors=['url'], evaluate=False,
			function=lambda x: x
		)
		self._pensieve['disambiguation'] = False
		self._pensieve['redirected_from'] = None

	def _load_from_id(self):
		self._pensieve.store(
			key='search_result', precursors=['original_id', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=None, id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)
		self._parse_search_results(
			keys=['id', 'title', 'page', 'redirected_from', 'language', 'namespace', 'full_url', 'disambiguation']
		)
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
		self._parse_search_results(
			keys=['id', 'title', 'page', 'redirected_from', 'language', 'namespace', 'full_url', 'disambiguation']
		)
		self._pensieve.store(key='url', precursors=['page'], function=lambda x: x['fullurl'], evaluate=False)
		self._get_url_response()

	def _load_the_rest(self):
		self._pensieve.store(
			key='base_url', precursors=['url'], evaluate=False, materialize=False,
			function=lambda x: x[:x.find('/wiki/')]
		)

		# main parts
		def _add_see_also_flag(x):
			x = re.sub(
				r'<h2>.*>see also<.*</h2>', '<h2>SEEALSO</h2><ul><li><a href="http://SEEALSO" title="SEEALSO">SEEALSO</a></li></ul>',
				x,
				flags=re.IGNORECASE
			)
			x = re.sub(
				r'<h2>.*>references<.*</h2>', '<h2>SEEALSO</h2><ul><li><a href="http://SEEALSO" title="SEEALSO">SEEALSO</a></li></ul>',
				x,
				flags=re.IGNORECASE
			)
			return x

		self._pensieve.store(
			key='body', precursors=['url_response'], evaluate=False,
			function=lambda x: BeautifulSoup(
				_add_see_also_flag(x.text),
				'lxml'
			)
		)

		self._pensieve.store(
			key='info_box', precursors=['body'], evaluate=False,
			function=lambda x: InfoBox(x.find(name='table', attrs={'class': 'infobox'}), extract=True)
		)

		self._pensieve.store(
			key='vertical_navigation_box', precursors=['body'], evaluate=False,
			function=lambda x: get_vertical_navigation_box(x, extract=True)
		)

		self._pensieve.store(
			key='navigation_boxes', precursors=['body'], evaluate=False,
			function=lambda x: get_navigation_boxes(x, extract=True)
		)

		self._pensieve.store(
			key='category_box', precursors=['body'], evaluate=False,
			function=lambda x: get_category_box(x, extract=True)
		)

		# end of main parts

		self._pensieve.store(
			key='paragraphs_and_tokens', precursors=['body'], evaluate=False,
			function=lambda x: get_paragraphs_and_tokens(soup=x, num_tokens=100)
		)

		self._pensieve.store(
			key='paragraphs', precursors=['paragraphs_and_tokens'], evaluate=False,
			function=lambda x: x['paragraphs']
		)

		self._pensieve.store(
			key='tokens', precursors=['paragraphs_and_tokens'], evaluate=False,
			function=lambda x: x['tokens']
		)


		self._pensieve.store(
			key='category_links', precursors=['category_box', 'base_url'], evaluate=False,
			function=lambda x: find_links(element=x['category_box'], base=x['base_url'])
		)

		self._pensieve.store(
			key='categories', precursors=['category_links'], evaluate=False,
			function=get_categories
		)

		self._pensieve.store(
			key='signature', precursors=['categories', 'info_box', 'tokens'], evaluate=False,
			function=lambda x: get_page_signature(
				tokens=x['tokens'], info_box=x['info_box'], categories=x['categories']
			)
		)

		self._pensieve.store(
			key='disambiguation_results',
			precursors=['disambiguation', 'body', 'base_url'],
			evaluate=False,
			function=lambda x: get_disambiguation_results(
				disambiguation=x['disambiguation'], html=x['body'], base_url=x['base_url']
			)
		)

		self._pensieve.store(
			key='tables',
			precursors=['body', 'base_url'],
			evaluate=False,
			function=lambda x: [
				standardize_columns(data=read_table(table=table, parse_links=True, base_url=x['base_url']))
				for table in x['body'].find_all('table', attrs={'class': 'wikitable'})
			]
		)

		def _get_anchors_and_links(html, base_url):

			def is_good_link(link):
				unacceptable = [
					'/w/index.php?', '/wiki/Special:', '/wiki/Help:',
					'/wiki/Wikipedia:', 'https://foundation.wikimedia.org',
					'/wiki/Talk:', '/wiki/Portal:', '/shop.wikimedia.org',
					'www.mediawiki.org', '/wiki/Main_Page', 'wikimediafoundation.org',
					'/wiki/Template:', '/wiki/Template_talk:'
				]
				for x in unacceptable:
					if x in link:
						return False
				return True

			table_links = {}
			list_links = {}
			ordered_list_links = {}

			for table in html.find_all('table'):
				for item in table.find_all('li'):
					if table.find_all('a'):
						link = parse_link(item, base=base_url)
						if link is not None:
							if link['url'] == 'http://SEEALSO':
								break  # out of both loops
							if is_good_link(link['url']):  # and ':' not in link['url']:
								table_links[link['url']] = link
				else:
					continue
				break

			for ordered_list in html.find_all('ol'):
				for item in ordered_list.find_all('li'):
					if item.find('a'):
						link = parse_link(item, base=base_url)
						if isinstance(link, Link):
							if link.url == 'http://SEEALSO':
								break
							if is_good_link(link.url):  # and ':' not in link['url']:
								ordered_list_links[link.url] = link
				else:
					continue
				break

			for item in html.find_all('li'):
				if item.find('a'):
					link = parse_link(item, base=base_url)
					if isinstance(link, Link):
						if link.url == 'http://SEEALSO':
							break
						if is_good_link(link.url):  # and ':' not in link['url']:
							if link.url not in table_links and link.url not in ordered_list_links:
								list_links[link.url] = link

			return {
				'list_link_and_anchors': list(list_links.values()),
				'table_links_and_anchors':list(table_links.values())
			}

		self._pensieve.store(
			key='link_and_anchors', precursors=['body', 'base_url'], evaluate=False,
			function=lambda x: _get_anchors_and_links(html=x['body'], base_url=x['base_url'])
		)

		self._pensieve.store(
			key='link_and_anchor_list', precursors=['link_and_anchors'], evaluate=False,
			function=lambda x: x['list_link_and_anchors']
		)

		self._pensieve.store(
			key='nested_link_and_anchor_lists', precursors=['body', 'base_url'], evaluate=False,
			function=lambda x: get_lists(element=x['body'], links_only=True, base=x['base_url'])
		)

		# ANCHORS IN A PAGE
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
				result = [x for x in result if len(x) > 0 or not isinstance(x, list)]
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
			function=lambda x: get_page_summary(page=self, id=x['id'], title=x['title'])
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
			key='summary_tokens', precursors=['summary'], evaluate=False, materialize=False,
			function=tokenize
		)

	def _get_json(self, id, title):
		id = str(id)
		html_query_parameters = get_html_parameters(id=id, title=title)
		html_request = self.request(parameters=html_query_parameters, format='json')
		return html_request['query']['pages'][id]['revisions'][0]['*']

	def _get_content(self, id, title):
		id = str(id)
		content_parameters = get_content_parameters(id=id, title=title)
		content_request = self.request(parameters=content_parameters, format='json')
		return content_request['query']['pages'][id]




