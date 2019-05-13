from .. import Navigator
from .Query import Query


class SearchEngine:
	def __init__(self, base_url, navigator=None):
		"""
		:type base_url: str
		:type navigator: Navigator or NoneType
		"""
		self._base_url = base_url
		self._navigator = navigator or Navigator()
		self._elapsed_time = 0
		self._num_queries = 0
		self._parser = 'lxml'
		self._get_json_back = False
		self._request_method = None

	def reset(self):
		self._elapsed_time = 0
		self._num_queries = 0

	@property
	def query_speed(self):
		return self._elapsed_time / self._num_queries

	@property
	def navigator(self):
		"""
		:rtype: Navigator
		"""
		return self._navigator

	@property
	def url(self):
		"""
		:rtype: str
		"""
		return self._base_url

	def get_search_url(self, query, **kwargs):
		"""
		:type query: str
		:rtype: str
		"""
		return f'{self.url}/search?q={query}'

	@classmethod
	def parse_search_results(cls, query, response_key, results_key):
		raise RuntimeError('this is just a place holder')

	def search(self, query, element_id=None, timeout_exception='error', **kwargs):
		"""
		:type query: str
		:param callable or NoneType search_function: a function that can be called on html and returns results
		:rtype: list
		"""
		query = Query(
			query=query, request_method=self._request_method,
			get_json_back=self._get_json_back, element_id=element_id, arguments=kwargs,
			timeout_exception=timeout_exception, parser=self._parser,
		)
		query.store(
			key='url', precursors=['query', 'arguments'],
			function=lambda x: self.get_search_url(query=x['query'], **x['arguments'])
		)
		response_key = 'response'
		query.store(
			key=response_key,
			precursors=['url', 'request_method', 'get_json_back', 'element_id', 'timeout_exception', 'parser'],
			function=lambda x: self.navigator.get(
				url=x['url'], request_method=x['request_method'], element_id=x['element_id'],
				timeout_exception=x['timeout_exception'], parser=x['parser'], get_json_back=x['get_json_back']
			)
		)
		self.parse_search_results(response_key=response_key, results_key='results', query=query)

		return query
