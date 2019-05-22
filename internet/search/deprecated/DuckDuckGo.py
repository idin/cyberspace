from .SearchEngine import SearchEngine, Navigator
from .Query import Query


class DuckDuckGo(SearchEngine):
	def __init__(self, navigator=None, use_api=True):
		"""
		:type navigator: Navigator
		"""
		super().__init__(base_url='https://duckduckgo.com', navigator=navigator)
		self._use_api = use_api
		if use_api:
			self._parser = None
			self._get_json_back = True

	def get_search_url(self, query, **kwargs):
		if self._use_api:
			return f'https://api.duckduckgo.com/?q={query}&format=json&no_html=1&no_redirect=1&skip_disambig=1'
		else:
			return f'{self.url}/?q={query}&ia=web'

	def parse_search_results(self, response_key, results_key, query):
		"""
		:type response_key: str
		:type results_key: str
		:type query: Query
		:rtype: list[dict[str,str]]
		"""
		if self._use_api:
			return query[response_key]
		else:
			query.store(key='links', precursors=[response_key], function=lambda x: x.find(attrs={'id': 'links'}))
			query.store(
				key='raw_results', precursors=['links'], function=lambda x: x.find_all(attrs={'class': 'result__a'})
			)
			query.store(
				key=results_key, precursors=['raw_results'],
				function=lambda x: [
					{'url': result.attrs['href'], 'text': result.get_text()}
					for result in x if not result.attrs['href'].startswith('https://duckduckgo.com')
				]
			)
		return query[results_key]
