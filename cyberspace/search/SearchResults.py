from silverware import find_links
from ..wikipedia import is_wikipedia_page_url
from .is_yahoo_finance_search_url_function import is_yahoo_finance_search_url

from bs4 import BeautifulSoup
from pensieve import Pensieve


class SearchResults:
	def __init__(self, api, query):
		self._api = api
		self._pensieve = Pensieve(safe=False, warn_unsafe=False)
		self._pensieve['query'] = query

	def _get_results(self):
		self._pensieve.store(
			key='response', precursors=['search_url'], function=lambda x: self.api.request(x),
			materialize=False, evaluate=False
		)
		self._pensieve.store(
			key='html', precursors=['response'], function=lambda x: x.text,
			evaluate=False
		)
		self._pensieve.store(
			key='parsed_html', precursors=['html'], function=lambda x: BeautifulSoup(x, 'lxml'),
			evaluate=False
		)

	@property
	def api(self):
		"""
		:rtype: .Search_class.Bing
		"""
		return self._api

	def __getitem__(self, item):
		return self._pensieve[item]


class BingSearchResults(SearchResults):
	def __init__(self, api, query, site=None):
		super().__init__(api=api, query=query)
		self._pensieve['site'] = site

		self._pensieve.store(
			key='search_url', precursors=['query', 'site'],
			function=lambda x: self.api.get_bing_search_url(query=x['query'], site=x['site'])
		)
		self._get_results()

		self._pensieve.store(
			key='links', precursors=['parsed_html'],
			function=lambda x: [
				link for link in find_links(element=x, base=None)
				if link.url.startswith('http://') or link.url.startswith('https://')
			],
			evaluate=False
		)

		self._pensieve.store(
			key='wikipedia_links', precursors=['links'],
			function=lambda x: [link for link in x if is_wikipedia_page_url(url=link['url'])]
		)


class YahooSearchResults(SearchResults):
	def __init__(self, api, query, num_results=None, site=None):
		super().__init__(api=api, query=query)

		self._pensieve['site'] = site
		self._pensieve['num_results'] = num_results

		self._pensieve.store(
			key='search_url', precursors=['query', 'num_results', 'site'],
			function=lambda x: self.api.get_yahoo_search_url(
				query=x['query'], num_results=x['num_results'], site=x['site']
			)
		)
		self._get_results()
		self._pensieve.store(
			key='links', precursors=['parsed_html'],
			function=lambda x: [
				link for link in find_links(element=x, base=None)
				if link.url.startswith('http://') or link.url.startswith('https://')
			],
			evaluate=False
		)

		self._pensieve.store(
			key='wikipedia_links', precursors=['links'],
			function=lambda x: [link for link in x if is_wikipedia_page_url(url=link.url)]
		)

		self._pensieve.store(
			key='yahoo_finance_search_urls', precursors=['links'],
			function=lambda x: [link.url for link in x if is_yahoo_finance_search_url(url=link.url)]
		)
