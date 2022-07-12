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
from collections import Counter
from ravenclaw.wrangling import standardize_columns
from chronometry.progress import ProgressBar

from soupspoon import Spoon, Link, find_links
from bs4 import BeautifulSoup
from pandas import DataFrame
import warnings
from multiprocessing.pool import ThreadPool


class WikipediaPage:
	def __init__(
			self, wikipedia, id=None, url=None, title=None, namespace=None, redirect=True, disambiguation_url=None,
			ignore_error=False, n_jobs=1
	):
		self._wikipedia = wikipedia
		self._id = id
		self._url = url
		self._title = title
		self._ignore_error = ignore_error
		self._n_jobs = n_jobs
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

	@property
	def pensieve(self):
		"""
		:rtype: Pensieve
		"""
		return self._pensieve

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

	def _setup_pensieve(self):
		self._pensieve = Pensieve(
			lazy=True, materialize=True,
			function_durations=self.wikipedia.function_durations, hide_ignored=False
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
		:rtype: cyberspace.Wikipedia
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
		if self.wikipedia.has_memory() and item != 'url':
			value = self.wikipedia.memory.get_page_attribute(url=self.url, attribute=item)
			if value is not None and value != False:
				return value

		value = self.pensieve[item]

		if self.wikipedia.has_memory() and item != 'url':
			self.wikipedia.memory.set_page_attribute(url=self.url, attribute=item, value=value)

		return value

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
			return self['id']
		else:
			return self['original_id']

	@property
	def url(self):
		if 'url' not in self.pensieve:
			raise AttributeError(f'Page {self} does not have a url!')
		elif self.pensieve['url'] is None:
			raise AttributeError(f'Page {self} does not have a url!')
		return self.pensieve['url']

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
		self.pensieve['base_url'] = lambda url: url[:url.find('/wiki/')]

		self.pensieve['separated_body'] = lambda url_response: separate_body_from_navigation_and_info_box(
			url_response=url_response
		)

		self.pensieve['body'] = lambda separated_body: separated_body['body']

		self.pensieve['headers'] = lambda body: body.find_all(['h1', 'h2', 'h3'])

		self.pensieve['info_box'] = lambda separated_body, base_url: InfoBox(
			separated_body['info_box'], base_url=base_url
		)

		self.pensieve['info_box_links'] = lambda info_box: [] if info_box is None else info_box.links

		self.pensieve['info_box_dictionary'] = lambda info_box: info_box._dictionary.copy()

		self.pensieve['vertical_navigation_box'] = lambda separated_body: separated_body['vertical_navigation_box']

		self.pensieve['navigation_boxes'] = lambda separated_body: [box for box in separated_body['navigation_boxes']]

		self.pensieve['category_box'] = lambda separated_body: separated_body['category_box']

		self.pensieve['body_links'] = lambda body, base_url: find_links(body, base=base_url)

		def _group_links(body_links):
			"""
			:type body_links: list[Link]
			"""
			def __is_good_link(link):
				"""
				:type link: Link
				"""
				if link.url.startswith('http'):
					for string in ['#', 'index.php', 'redlink=1', 'edit']:
						if string in link.url:
							return False
					else:
						return True
				else:
					return False

			groups = []
			for link in body_links:
				if __is_good_link(link) and is_wikipedia_page_url(link.url):
					subpage = self.wikipedia.get_page(url=link.url)
					if len(groups) == 0:
						groups.append(
							{'categories': subpage.categories.copy(), 'links': {link}}
						)
					else:

						best_group = None
						for group in groups:
							# if the subpage has any common category with this category
							common_categories = group['categories'].intersection(subpage.categories)
							n_common = len(common_categories)
							if best_group is None:
								if n_common > 0:
									group['categories'] = group['categories'].union(subpage.categories)
									group['links'].add(link)
									best_group = (group, n_common)
							elif n_common > best_group[1]:
								group['categories'] = group['categories'].union(subpage.categories)
								group['links'].add(link)
								best_group = (group, n_common)
						if best_group is None:
							groups.append({'categories': subpage.categories.copy(), 'links': {link}})
			return groups

		self.pensieve['body_links_grouped'] = _group_links

		self.pensieve['paragraphs'] = lambda body: get_main_paragraphs(body=body)

		self.pensieve['paragraph_links'] = lambda paragraphs, base_url: [
			[
				link.url for link in Spoon.find_links(element=paragraph, base_url=base_url) if isinstance(link, Link)
			]
			for paragraph in paragraphs
		]

		def _get_categories(category_box, base_url):
			category_links = Spoon.find_links(
				element=category_box, base_url=base_url
			)
			def __clean_category_link(link):
				if link.text.startswith('Category:'):
					new_text = link.text[len('Category:'):].strip()
					return Link(url=link.url, text=new_text)
				else:
					return link

			if isinstance(category_links, (set, list, tuple)):
				return {__clean_category_link(link) for link in category_links if isinstance(link, Link)}
			else:
				return set()

		self.pensieve['categories'] = _get_categories

		self.pensieve['disambiguation_results'] = lambda disambiguation, body, base_url: get_disambiguation_results(
			disambiguation=disambiguation, html=body, base_url=base_url
		)

		self.pensieve['tables'] = lambda body, base_url: [
			standardize_columns(data=table)
			for table in Spoon.filter(
				soup=body, name='table', attributes={'class': 'wikitable'}
			).read_tables(base_url=base_url, parse_links=True)
		]

		self.pensieve['table_links'] = lambda tables: find_main_links_in_tables(tables=tables)

		self.pensieve['anchors_and_links'] = lambda body, base_url: get_anchors_and_links(soup=body, base_url=base_url)

		self.pensieve['link_and_anchor_list'] = lambda anchors_and_links: anchors_and_links['list_links_and_anchors']

		self.pensieve['nested_link_and_anchor_lists'] = lambda body, base_url: Spoon.get_lists(
			element=body, links_only=True, base_url=base_url
		)

		# 	LINKS IN A PAGE
		def _remove_anchors(link_lists):
			if isinstance(link_lists, list):
				result = [_remove_anchors(x) for x in link_lists if x is not None]
				return [x for x in result if x is not None]
			elif isinstance(link_lists, Link):
				if link_lists.url.startswith('#'):
					return None
				else:
					return link_lists
			else:
				return link_lists

		self.pensieve['nested_link_lists'] = lambda nested_link_and_anchor_lists: _remove_anchors(
			link_lists=nested_link_and_anchor_lists
		)

		self.pensieve['link_list'] = lambda link_and_anchor_list: _remove_anchors(link_lists=link_and_anchor_list)

		# 	ANCHORS IN A PAGE
		def _remove_nonanchors(link_lists):
			if isinstance(link_lists, list):
				result = [_remove_nonanchors(x) for x in link_lists if x is not None]
				return [x for x in result if x is not None]
			elif isinstance(link_lists, Link):
				if not link_lists.url.startswith('#'):
					return None
				else:
					return link_lists
			else:
				return link_lists

		self.pensieve['nested_anchor_lists'] = lambda nested_link_and_anchor_lists: _remove_nonanchors(
			link_lists=nested_link_and_anchor_lists
		)

		self.pensieve['anchor_list'] = lambda link_and_anchor_list: _remove_nonanchors(link_lists=link_and_anchor_list)

		self.pensieve['summary'] = lambda id, title: get_page_summary(page=self, id=id, title=title)

		self.pensieve['content'] = lambda id, title: self._get_content(id=id, title=title)

		self.pensieve['extract'] = lambda content: content['extract']

		self.pensieve['revision_id'] = lambda content: content['revisions'][0]['revid']

		self.pensieve['parent_id'] = lambda content: content['revisions'][0]['parentid']

	def keys(self):
		return self.pensieve.keys()

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

	@property
	def categories(self):
		"""
		:rtype: set[str]
		"""
		return self['categories']

	def __hashkey__(self):
		return (repr(self.url), repr(self.__class__))

	def __hash__(self):
		return hash(self.__hashkey__())

	# def __hashkey__(self):
	#	return (self.__class__.__name__, tuple(getattr(self, name) for name in self._STATE_ATTRIBUTES_))