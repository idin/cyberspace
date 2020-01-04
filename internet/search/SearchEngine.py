from .SearchResults import BingSearchResults, YahooSearchResults

from chronometry import MeasurementSet, get_elapsed, get_now

import requests
from requests.utils import quote
import warnings
import time


class SearchEngine:
	def __init__(self, rate_limit_wait_seconds=0.01, cache=None):
		"""
		:param float rate_limit_wait_seconds: wait between requests
		:param disk.cache_class.Cache cache:
		"""
		self._rate_limit_wait = rate_limit_wait_seconds
		self._rate_limit_last_call = None

		self._cache = cache

		if self._cache:
			self.request = self._cache.make_cached(
				id='search_engine_request_function',
				function=self._request,
				condition_function=self._request_result_valid,
				sub_directory='request'
			)

		else:
			self.request = self._request

		self._function_durations = MeasurementSet()

	@staticmethod
	def get_bing_search_url(query, site=None):
		"""
		:type query: str
		:type site: str
		:rtype: str
		"""
		full_query = quote(query).replace('%20', '+')
		if site is not None:
			full_query += f'+site:{site}'
		return 'https://www.bing.com/search?q=' + full_query

	def search_bing(self, query, site=None):
		return BingSearchResults(api=self, query=query, site=site)

	@staticmethod
	def get_yahoo_search_url(query, num_results=None, site=None):
		"""
		:type query: str
		:type site: str
		:rtype: str
		"""
		full_query = ''
		if num_results is not None:
			full_query += f'n={num_results}&'

		full_query += 'p='+quote(query).replace('%20', '+')

		if site is not None:
			query += f'&vs:{site}'

		return  'https://search.yahoo.com/search?' + full_query

	def search_yahoo(self, query, site=None, num_results=None):
		return YahooSearchResults(api=self, query=query, num_results=num_results, site=site)

	@staticmethod
	def _request_result_valid(response):
		if response.status_code == 200:
			return True
		else:
			warnings.warn(f'response status code: {response.status_code}')
			return False

	def _request(self, url=None, header=None):
		"""
		:type parameters: dict
		:rtype: dict
		"""
		if url is None:
			raise ValueError('url cannot be empty for non-json request!')

		# headers = {'User-Agent': self._user_agent}

		if self._rate_limit_wait and self._rate_limit_last_call:
			wait_time = self._rate_limit_wait - get_elapsed(start=self._rate_limit_last_call, unit='s')
			if wait_time > 0:
				time.sleep(wait_time)
		with warnings.catch_warnings():
			warnings.filterwarnings('ignore')
			result = requests.get(url, verify=False)

		if self._rate_limit_wait:
			self._rate_limit_last_call = get_now()
		return result
