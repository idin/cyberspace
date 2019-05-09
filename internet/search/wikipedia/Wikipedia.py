# p
from copy import deepcopy
import requests
import re
import time
import warnings

# i
from chronology import get_now, get_elapsed_seconds
from slytherin.collections import remove_list_duplicates, flatten
from abstract import Graph
from interaction import ProgressBar

from .exceptions import HTTPTimeoutError, WikipediaException
from .Page import Page


class Wikipedia:
	def __init__(
			self, language='en',
			user_agent='wikipedia (https://github.com/goldsmith/Wikipedia/)',
			rate_limit_wait_seconds=0.01,
			cache=None,
	):
		"""
		:param str language: such as 'en'
		:param str user_agent:
		:param float rate_limit_wait_seconds: wait between requests
		:param disk.cache_class.Cache cache:
		"""
		self._language = language
		self._user_agent = user_agent
		self._rate_limit_wait = rate_limit_wait_seconds
		self._rate_limit_last_call = None
		self._cache = cache
		if self._cache:
			self.request = self._cache.make_cached(
				id='wikipedia_request_function',
				function=self._request,
				condition_function=self._request_result_valid,
				sub_directory='request'
			)

			self.get_page_children = self._cache.make_cached(
				id='wikipedia_page_children_function',
				function=self._get_page_children,
				condition_function=None,
				sub_directory='page_children'
			)

			self.get_title_and_id = self._cache.make_cached(
				id='wikipedia_get_title_and_id_function',
				function=self._get_title_and_id,
				condition_function=None,
				sub_directory='title_and_id'
			)

		else:
			self.request = self._request
			self.get_page_children = self._get_page_children
			self.get_title_and_id = self._get_title_and_id

	@property
	def language(self):
		return self._language.lower()

	@property
	def api_url(self):
		return 'http://' + self.language + '.wikipedia.org/w/api.php'

	def _request_result_valid(self, result, parameters=None, url=None, format='json'):
		return True

	def _request(self, parameters=None, url=None, format='json'):
		"""
		:type parameters: dict
		:rtype: dict
		"""
		if format == 'json':
			if parameters is None:
				raise ValueError('parameters cannot be empty for json request!')
			parameters['format'] = 'json'
			if 'action' not in parameters:
				parameters['action'] = 'query'
		else:
			if url is None:
				raise ValueError('url cannot be empty for non-json request!')


		headers = {'User-Agent': self._user_agent}

		if self._rate_limit_wait and self._rate_limit_last_call:
			wait_time = self._rate_limit_wait - get_elapsed_seconds(start=self._rate_limit_last_call, end=get_now())
			if  wait_time > 0:
				time.sleep(wait_time)


		if format == 'json':
			r = requests.get(self.api_url, params=parameters, headers=headers)
			result = r.json()
		else:
			result = requests.get(url, headers=headers)
			# result = html.document_fromstring(r.text)
			# result = r.text

		if self._rate_limit_wait:
			self._rate_limit_last_call = get_now()
		return result

	def get_page(self, id=None, url=None, title=None, namespace=0, redirect=True):
		"""
		:type id: int or str or NoneType
		:type title: str or NoneType
		:rtype: Page
		"""
		return Page(id=id, url=url, title=title, namespace=namespace, api=self, redirect=redirect)

	def _get_title_and_id(self, url, redirect):
		try:
			_page = Page(api=self, url=url, redirect=redirect)
			return {'id': _page['id'], 'title': _page['title'], 'url': _page['url']}
		except Exception as e:
			return None

	def _get_page_children(self, id=None, url=None, title=None, namespace=0, redirect=True, echo=1):
		page = self.get_page(id=id, url=url, title=title, namespace=namespace, redirect=redirect)
		link_lists = page['link_lists']
		if link_lists:
			urls = remove_list_duplicates([link['url'] for link in flatten(link_lists)])
			wikipedia_urls = [url for url in urls if re.match('^https://.+\.wikipedia.org/', url)]
			non_php_urls = [url for url in wikipedia_urls if '/index.php?' not in url]

			pages = ProgressBar.map(
				function=lambda x: self.get_title_and_id(url=x, redirect=redirect),
				iterable=non_php_urls, echo=echo, text=page['url']
			)
			return [page for page in pages if page is not None]
		else:
			return []

	def get_page_graph(
			self, graph=None, id=None, url=None, title=None, namespace=0, redirect=True,
			max_depth=1, strict=True, ordering=True, echo=1
	):
		try:
			if graph:
				graph = deepcopy(graph)
			else:
				graph = Graph(obj=None, strict=strict, ordering=ordering)

			def _crawl(graph, url, title, id, parent_page_url, max_depth, depth, echo):
				if url not in graph:
					graph.add_node(name=url, label=title, value=id)
					if depth < max_depth:
						children = self.get_page_children(url=url, redirect=redirect, echo=echo)
						for child in children:
							_crawl(
								graph=graph, url=child['url'], title=child['title'], id=child['url'],
								parent_page_url=url, max_depth=max_depth, depth=depth + 1, echo=echo
							)
				if parent_page_url:
					graph.connect(start=parent_page_url, end=url)

			page = self.get_page(id=id, url=url, title=title, namespace=namespace, redirect=redirect)
			_crawl(
				graph=graph, url=page['url'], title=page['title'], id=page['id'], parent_page_url=None,
				max_depth=max_depth, echo=echo, depth=0
			)
			return graph
		except KeyboardInterrupt:
			warnings.warn('get_page_graph was interrupted by keyboard!')
			return graph

	def search(self, query, num_results=10, redirect=True):
		"""
		Do a Wikipedia search for `query`.
		:type query: str
		:param int num_results: the maxmimum number of results returned
		:type redirect: bool
		"""

		search_params = {
			'list': 'search',
			'srprop': '',
			'srlimit': num_results,
			'limit': num_results,
			'srsearch': query
		}

		raw_results = self.request(search_params)

		if 'error' in raw_results:
			if raw_results['error']['info'] in ('HTTP request timed out.', 'Pool queue is full'):
				raise HTTPTimeoutError(query)
			else:
				raise WikipediaException(raw_results['error']['info'])

		results = raw_results['query']['search']
		pages = [
			Page(api=self, id=d['pageid'], title=d['title'], namespace=d['ns'], redirect=redirect) for d in results
		]
		already_captured_urls = [page['url'] for page in pages]
		disambiguation_pages = [page for page in pages if page['disambiguation']]
		disambiguation_results = [
			Page(
				api=self, url=url_dictionary['url'], title=url_dictionary['text'],
				disambiguation_url=disambiguation_page['url']
			)
			for disambiguation_page in disambiguation_pages
			for url_dictionary in disambiguation_page['disambiguation_results']
			if url_dictionary['url'] not in already_captured_urls
		]
		#print(disambiguation_results)
		return pages + disambiguation_results
