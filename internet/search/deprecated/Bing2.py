from .SearchEngine import SearchEngine, Navigator
from .Query import Query


class Bing2(SearchEngine):
	def __init__(self, navigator=None):
		"""
		:type navigator: Navigator
		"""
		super().__init__(base_url='https://bing.com', navigator=navigator)

	def get_search_url(self, query, **kwargs):
		if 'results' in kwargs:
			return f'{self.url}/search?q={query}&results={kwargs["results"]}'
		else:
			return f'{self.url}/search?q={query}'

	@classmethod
	def parse_search_results(cls, query, response_key='html', results_key='results'):
		"""
		:type response_key: str
		:type results_key: str
		:type query: Query
		:rtype: list[dict[str,str]]
		"""
		query.store(key='b_content', precursors=[response_key], function=lambda x: x.find_all(attrs={'id': 'b_content'})[0])
		query.store(key='b_algo', precursors=['b_content'], function=lambda x: x.find_all(attrs={'class': 'b_algo'}))
		def get_headers(b_algo):
			headers = [x.find('h2') for x in b_algo]
			return [{'title': x.get_text(), 'url': x.find('a')['href']} for x in headers]

		query.store(key=results_key, precursors=['b_algo'], function=get_headers)
		return query[results_key]

