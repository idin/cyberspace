from .exceptions import PageError, RedirectError, ODD_ERROR_MESSAGE
from .InfoBox import InfoBox
from .get_wikipedia_id import get_wikipedia_id, get_page_title, get_page_language, get_page_namespace
from .Page_helpers import *
from .is_wikipedia_page_url import is_wikipedia_page_url
from .is_wikipedia_page_url import is_mobile_wikipedia_page_url
from .is_wikipedia_page_url import convert_mobile_wikipedia_page_url_to_normal_page

import re
from pensieve import Pensieve
from slytherin.collections import remove_list_duplicates, flatten
from ravenclaw.wrangling import standardize_columns
from chronometry.progress import ProgressBar

from silverware import Spoon
from bs4 import BeautifulSoup
from pandas import DataFrame
import warnings


class WikipediaPage:
	def __init__(
			self, wikipedia, id=None, url=None, title=None, namespace=None, redirect=True, disambiguation_url=None,
			ignore_error=False
	):
		self._wikipedia = wikipedia
		self._id = id
		self._url = url
		self._title = title
		self._ignore_error = ignore_error
		self._setup_pensieve()
		self.pensieve['namespace'] = namespace
		self.pensieve['redirect'] = redirect
		self.pensieve['disambiguation_url'] = disambiguation_url
		self._load_primary()

		try:
			self._load_the_rest()
		except Exception as e:
			warnings.warn(f'failed to load the rest id: "{self._id}", url: "{self._url}", title: "{self._title}"')
			if not ignore_error:
				raise e

	_STATE_ATTRIBUTES_ = ['_id', '_url', '_title', '_ignore_error']

	def __getstate__(self):
		state = {key: getattr(self, key) for key in self._STATE_ATTRIBUTES_}
		state['_pensieve'] = self._pensieve.get_contents()
		return state

	def __setstate__(self, state):
		for key, value in state.items():
			setattr(self, key, value)
		self._pensieve = state['_pensieve']
		self._load_primary()
		try:
			self._load_the_rest()
		except Exception as e:
			warnings.warn(f'failed to load the rest id: "{self._id}", url: "{self._url}", title: "{self._title}"')
			if not self._ignore_error:
				raise e

	def __hashkey__(self):
		return (self.__class__.__name__, tuple(getattr(self, name) for name in self._STATE_ATTRIBUTES_))

	def _setup_pensieve(self):
		self._pensieve = Pensieve(
			safe=False, function_durations=self.wikipedia.function_durations, warn_unsafe=False, hide_ignored=False
		)

	def _load_primary(self):
		if self._id or self._title or self._url:
			pass
		else:
			raise ValueError('Either id or title or url should be given!')
		if self._id:
			self.pensieve['original_id'] = self._id
			try:
				self._load_from_id()
			except Exception as e:
				warnings.warn(f'failed to load from id: "{self._id}"')
				if not self._ignore_error:
					raise e

		elif self._url:
			if is_wikipedia_page_url(url=self._url):
				if is_mobile_wikipedia_page_url(url=self._url):
					url = convert_mobile_wikipedia_page_url_to_normal_page(url=self._url)
				else:
					url = self._url

				self.pensieve['url'] = url
				try:
					self._load_from_url()
				except Exception as e:
					warnings.warn(f'failed to load from url: "{self._url}"')
					if not self._ignore_error:
						raise e
			else:
				raise ValueError(f'{self._url} does not match the wikipedia page pattern!')

		elif self._title:
			self.pensieve['original_title'] = self._title
			try:
				self._load_from_title()
			except Exception as e:
				warnings.warn(f'failed to load from title: "{self._title}"')
				if not self._ignore_error:
					raise e

	@property
	def wikipedia(self):
		"""
		:rtype: .Wikipedia_class.Wikipedia
		"""
		if self._wikipedia is None:
			raise AttributeError('Wikipedia API is missing!')
		else:
			return self._wikipedia

	def __eq__(self, other):
		"""
		:type other: WikipediaPage
		:rtype: bool
		"""
		if isinstance(other, self.__class__):
			return self['url'] == other['url']
		else:
			return False

	def __str__(self):
		if 'url' in self.pensieve:
			url = self.pensieve['url']
			return f'{self.title}: {url} '
		else:
			return f'{self.title}: {self.id} '

	def __repr__(self):
		return str(self)

	def __getitem__(self, item):
		return self.pensieve[item]

	def __graph__(self):
		return self.pensieve.__graph__()

	@property
	def title(self):
		"""
		:rtype: str
		"""
		if 'title' in self.pensieve:
			return self.pensieve['title']
		else:
			return self.pensieve['original_title']

	@property
	def id(self):
		"""
		:rtype: int
		"""
		if 'id' in self.pensieve:
			return self.pensieve['id']
		else:
			return self.pensieve['original_id']

	@property
	def url(self):
		if 'url' not in self.pensieve:
			raise AttributeError(f'Page {self} does not have a url!')
		elif self.pensieve['url'] is None:
			raise AttributeError(f'Page {self} does not have a url!')
		return self.pensieve['url']



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
		return 'http://' + self.wikipedia.language + '.wikipedia.org'

	@wikipedia.setter
	def wikipedia(self, wikipedia):
		"""
		:type wikipedia: .Wikipedia_class.Wikipedia
		"""
		self._wikipedia = wikipedia

	def get_children(self, echo=1):
		link_lists = self['link_list']
		if link_lists:
			urls = remove_list_duplicates([link.url for link in flatten(link_lists)])
			wikipedia_urls = [url for url in urls if re.match('^https://.+\.wikipedia.org/', url)]
			non_php_urls = [url for url in wikipedia_urls if '/index.php?' not in url]

			pages = ProgressBar.map(
				function=lambda x: self.__class__(url=x, redirect=self['redirect'], wikipedia=self.wikipedia),
				iterable=non_php_urls, echo=echo, text=self['url']
			)
			return pages
		else:
			return []

	def request(self, url=None, parameters=None, format='html'):
		return self.wikipedia.request(url=url, parameters=parameters, format=format)

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

		# since we only asked for disambiguation in pageprop,
		# if a pageprop is returned,
		# then the page must be a disambiguation page
		elif 'pageprops' in page:
			return {
				'id': int(id), 'title': title, 'page': page, 'redirected_from': redirected_from,
				'full_url': full_url, 'language': language, 'namespace': namespace, 'disambiguation': True
			}

		else:
			return {
				'id': int(id), 'title': title, 'page': page, 'redirected_from': redirected_from,
				'full_url': full_url, 'language': language, 'namespace': namespace, 'disambiguation': False
			}

	def _get_url_response(self):
		self.pensieve.store(
			key='url_response', precursors='url', evaluate=False,
			function=lambda x: self.request(url=x, format='response')
		)

	def _load_from_url(self):
		self._get_url_response()

		self.pensieve.store(
			key='original_id', precursors=['url_response'], evaluate=False,
			function=lambda x: get_wikipedia_id(x.text)
		)

		self.pensieve.store(
			key='search_result', precursors=['original_id', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=None, id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)

		self.pensieve.store(
			key='id', precursors=['url_response'], evaluate=False,
			function=lambda x: get_wikipedia_id(x.text)
		)
		self.pensieve.store(
			key='title', precursors=['url_response'], evaluate=False,
			function=lambda x: get_page_title(x.text)
		)
		self.pensieve.store(
			key='language', precursors=['url_response'], evaluate=False,
			function=lambda x: get_page_language(x.text)
		)
		self.pensieve.store(
			key='namespace', precursors=['url_response'], evaluate=False,
			function=lambda x: get_page_namespace(x.text)
		)
		self.pensieve.store(
			key='full_url', precursors=['url'], evaluate=False,
			function=lambda x: x
		)
		self.pensieve['disambiguation'] = False
		self.pensieve['redirected_from'] = None

	def _load_from_id(self):
		self.pensieve.store(
			key='search_result', precursors=['original_id', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=None, id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)
		self.pensieve.decouple(key='search_result', prefix='')

		try:
			self.pensieve.store(
				key='json', precursors=['id', 'title'], evaluate=False,
				function=lambda x: self._get_json(id=x['id'], title=x['title'])
			)
		except Exception as e:
			display(self.pensieve)
			raise e

		self.pensieve.store(key='url', precursors=['page'], function=lambda x: x['fullurl'], evaluate=False)
		self._get_url_response()

	def _load_from_title(self):
		self.pensieve.store(
			key='search_result', precursors=['original_title', 'redirect'], evaluate=False,
			function=lambda x: self._search_page(
				title=x['original_title'], id=None, redirect=x['redirect'],
				redirected_from=None
			)
		)
		self.pensieve.decouple(key='search_result')
		self.pensieve.store(
			key='json', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_json(id=x['id'], title=x['title'])
		)
		self.pensieve.store(
			key='url', precursors=['page'],
			function=lambda x: x['fullurl'], evaluate=False
		)
		self._get_url_response()

	def _load_the_rest(self):
		self.pensieve.store(
			key='base_url', precursors=['url'],
			evaluate=False, materialize=False,
			function=lambda x: x[:x.find('/wiki/')]
		)

		# main parts
		def _add_see_also_flag(x):
			x = re.sub(
				r'<h2>.*>(references|external\s+links|notes\s+and\s+references|see\s+also)<.*</h2>',
				'<h2>SEEALSO</h2><ul><li><a href="http://SEEALSO" title="SEEALSO">SEEALSO</a></li></ul>',
				x,
				flags=re.IGNORECASE
			)
			return x

		def _get_beautiful_soup(url_response):
			text = _add_see_also_flag(url_response.text.replace('\\u0026', 'and').replace('&amp;', 'and'))
			soup = BeautifulSoup(text, 'lxml')
			for element in soup.find_all(name='div', attrs={'id': 'mw-panel'}):
				element.decompose()
			for element in soup.find_all(name='div', attrs={'id': 'mw-head'}):
				element.decompose()
			return soup


		self.pensieve.store(
			key='separated_body', precursors=['url_response'], evaluate=False,
			function=lambda url_response: separate_body_from_navigation_and_info_box(
				url_response=url_response
			)
		)

		self.pensieve.store(
			key='body',
			function=lambda separated_body: separated_body['body']
		)


		self.pensieve.store(
			key='headers', precursors=['body'], evaluate=False,
			function=lambda x: x.find_all(['h1', 'h2', 'h3'])
		)


		self.pensieve.store(
			key='info_box', evaluate=False,
			function=lambda separated_body: InfoBox(separated_body['info_box'])
		)

		self.pensieve.store(
			key='vertical_navigation_box',  evaluate=False,
			function=lambda separated_body: separated_body['vertical_navigation_box']
		)

		self.pensieve.store(
			key='navigation_boxes', evaluate=False,
			function=lambda separated_body: [
				box for box in separated_body['navigation_boxes']
			]
		)

		self.pensieve.store(
			key='category_box', evaluate=False,
			function=lambda separated_body: separated_body['category_box']
		)

		# end of main parts

		self.pensieve.store(
			key='paragraphs', precursors=['body'], evaluate=False,
			function=lambda x: get_main_paragraphs(body=x)
		)

		self.pensieve.store(
			key='paragraph_links', precursors=['paragraphs', 'base_url'], evaluate=False,
			function=lambda x: [
				[
					link.url
					for link in Spoon.find_links(element=paragraph, base_url=x['base_url'])
					if isinstance(link, Link)
				]
				for paragraph in x['paragraphs']
			]
		)

		self.pensieve.store(
			key='category_links', evaluate=False,
			function=lambda category_box, base_url: Spoon.find_links(
				element=category_box, base_url=base_url
			)
		)

		self.pensieve.store(
			key='categories', evaluate=False,
			function=get_categories
		)

		self.pensieve.store(
			key='disambiguation_results',
			precursors=['disambiguation', 'body', 'base_url'],
			evaluate=False,
			function=lambda x: get_disambiguation_results(
				disambiguation=x['disambiguation'], html=x['body'], base_url=x['base_url']
			)
		)

		self.pensieve.store(
			key='tables',
			precursors=['body', 'base_url'],
			evaluate=False,
			function=lambda x: [
				standardize_columns(data=table)
				for table in Spoon.filter(
					soup=x['body'], name='table', attributes={'class': 'wikitable'}
				).read_tables(base_url=x['base_url'], parse_links=True)
			]
		)

		self.pensieve.store(
			key='table_links',
			precursors=['tables'],
			evaluate=False,
			function=find_main_links_in_tables
		)

		self.pensieve.store(
			key='link_and_anchors', precursors=['body', 'base_url'], evaluate=False,
			function=lambda x: get_anchors_and_links(soup=x['body'], base_url=x['base_url'])
		)

		self.pensieve.store(
			key='link_and_anchor_list', precursors=['link_and_anchors'], evaluate=False,
			function=lambda x: x['list_link_and_anchors']
		)

		self.pensieve.store(
			key='nested_link_and_anchor_lists', precursors=['body', 'base_url'], evaluate=False,
			function=lambda x: Spoon.get_lists(element=x['body'], links_only=True, base_url=x['base_url'])
		)

		# 	LINKS IN A PAGE
		def _remove_anchors(link_lists):
			if isinstance(link_lists, list):
				return [_remove_anchors(x) for x in link_lists if x is not None]
			elif isinstance(link_lists, Link):
				if link_lists.url.startswith('#'):
					return None
				else:
					return link_lists

		# 	LINKS IN A PAGE
		def _remove_nonanchors(link_lists):
			if isinstance(link_lists, list):
				return [_remove_anchors(x) for x in link_lists if x is not None]
			elif isinstance(link_lists, Link):
				if not link_lists.url.startswith('#'):
					return None
				else:
					return link_lists

		self.pensieve.store(
			key='nested_anchor_lists', precursors=['nested_link_and_anchor_lists'], evaluate=False,
			function=_remove_nonanchors
		)

		self.pensieve.store(
			key='anchor_list', precursors=['link_and_anchor_list'], evaluate=False,
			function=_remove_nonanchors
		)



		self.pensieve.store(
			key='nested_link_lists', precursors=['nested_link_and_anchor_lists'], evaluate=False,
			function=_remove_anchors
		)

		self.pensieve.store(
			key='link_list', precursors=['link_and_anchor_list'], evaluate=False,
			function=_remove_anchors
		)

		self.pensieve.store(
			key='summary', precursors=['id', 'title'], evaluate=False,
			function=lambda x: get_page_summary(page=self, id=x['id'], title=x['title'])
		)

		self.pensieve.store(
			key='content', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_content(id=x['id'], title=x['title'])
		)

		self.pensieve.store(
			key='extract', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['extract']
		)

		self.pensieve.store(
			key='revision_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['revid']
		)

		self.pensieve.store(
			key='parent_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['parentid']
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

	@property
	def body(self):
		"""
		:rtype: BeautifulSoup
		"""
		return self['body']

	@property
	def tables(self):
		"""
		:rtype: list[DataFrame]
		"""
		return self['tables']

	def __hashkey__(self):
		return (repr(self.url), repr(self.__class__))