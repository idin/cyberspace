# p
from copy import deepcopy
import requests
import time
import warnings

# i
from chronology import MeasurementSet, get_elapsed, get_now
from abstract import Graph

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

			self.get_title_and_id = self._cache.make_cached(
				id='wikipedia_get_title_and_id_function',
				function=self._get_title_and_id,
				condition_function=None,
				sub_directory='title_and_id'
			)

		else:
			self.request = self._request
			self.get_title_and_id = self._get_title_and_id

		self._function_durations = MeasurementSet()

	@property
	def function_durations(self):
		"""
		:rtype: MeasurementSet
		"""
		return self._function_durations

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
			wait_time = self._rate_limit_wait - get_elapsed(start=self._rate_limit_last_call, unit='s')
			if wait_time > 0:
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
		:type url: str or NoneType
		:type title: str or NoneType
		:rtype: Page
		"""
		return Page(id=id, url=url, title=title, namespace=namespace, api=self, redirect=redirect)

	def _get_title_and_id(self, url, redirect):
		try:
			_page = self.get_page(url=url, redirect=redirect)
			return {'id': _page['id'], 'title': _page['title'], 'url': _page['url']}
		except Exception as e:
			return None

	def get_page_graph(
			self, graph=None, id=None, url=None, title=None, namespace=0, redirect=True,
			max_depth=1, strict=True, ordering=True, echo=1
	):
		try:
			if graph:
				graph = deepcopy(graph)
			else:
				graph = Graph(obj=None, strict=strict, ordering=ordering)

			def _crawl(_graph, _page, _parent_page, _max_depth, _depth, _echo, _crawl_completed):
				if _page['url'] not in _graph:
					_graph.add_node(name=_page['url'], label=_page['title'], value=_page)

				if _parent_page is not None:
					_graph.connect(start=_parent_page['url'], end=_page['url'], if_edge_exists='ignore')

				# to avoid crawling the children of a page for a second time we add the url of the parent page in
				# crawl_completed at the end
				if _page['url'] not in _crawl_completed and _depth < _max_depth:
					for child in _page.get_children(echo=_echo):
						_crawl(
							_graph=_graph, _page=child,
							_parent_page=_page, _max_depth=_max_depth, _depth=_depth + 1, _echo=_echo,
							_crawl_completed=_crawl_completed
						)
					_crawl_completed.append(_page['url'])

			page = self.get_page(id=id, url=url, title=title, namespace=namespace, redirect=redirect)
			_crawl(
				_graph=graph, _page=page, _parent_page=None,
				_max_depth=max_depth, _echo=echo, _depth=0, _crawl_completed=[]
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

		return pages + disambiguation_results

	def get_performance(self):
		return self.function_durations.summary_data
