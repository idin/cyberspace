import requests
from requests.adapters import SSLError
from time import sleep
import warnings
from bs4 import BeautifulSoup
from disk import Cache, Path
from chronometry import get_now, get_elapsed


class Scraper:
	def __init__(self, name, expire_in=None, rate_limit_wait_seconds=0.01, cache=None, num_request_tries=4):
		if isinstance(cache, (str, Path)):
			cache = Cache(path=cache)

		self._name = name
		self._rate_limit_wait = rate_limit_wait_seconds
		self._rate_limit_last_call = None
		self._num_request_tries = num_request_tries
		self._expire_in = expire_in
		self._cache = cache
		self._create_cached_functions()

	def _create_cached_functions(self):
		if self.cache:
			self.request = self.cache.make_cached(
				id=f'{self._name}_request',
				function=self._request,
				sub_directory=f'{self._name}_request',
				expire_in=self._expire_in
			)
			self.get_request_soup = self._get_request_soup
		else:
			self.request = self._request
			self.get_request_soup = self._get_request_soup

	def _get_state_attribute_names(self):
		return ['_name', '_rate_limit_wait', '_rate_limit_last_call', '_num_request_tries', '_expire_in', '_cache']

	def __getstate__(self):
		return {attribute_name: getattr(self, attribute_name) for attribute_name in self._get_state_attribute_names()}

	def __setstate__(self, state):
		for key, value in state.items():
			setattr(self, key, value)
		self._create_cached_functions()

	@property
	def cache(self):
		"""
		:rtype: Cache or NoneType
		"""
		return self._cache

	def _request(self, url, verify=False):
		error = None
		for i in range(1, self._num_request_tries + 1):
			try:
				if self._rate_limit_wait and self._rate_limit_last_call:
					wait_time = self._rate_limit_wait - get_elapsed(start=self._rate_limit_last_call, unit='s')
					if wait_time > 0:
						sleep(wait_time)
				with warnings.catch_warnings():
					warnings.simplefilter('ignore')
					result = requests.get(url, verify=verify)
				break
			except SSLError as error:
				print(f'try {i}, error with get request with url="{url}"')
				warnings.warn(str(e))
				sleep(0.001 * 10 ** i)
		else:
			print(f'failed after {self._num_request_tries} requests!')
			raise error

		if self._rate_limit_wait:
			self._rate_limit_last_call = get_now()

		return result

	def _get_request_soup(self, content, features='lxml'):
		return BeautifulSoup(content, features)

	def get_soup(self, url, verify=False):
		"""
		:type url: str
		:rtype: BeautifulSoup
		"""
		return self.get_request_soup(content=self.request(url=url, verify=verify).content)
