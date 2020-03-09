import requests
from disk import Cache
from requests.adapters import SSLError
from time import sleep
from chronometry import get_now, get_elapsed
import warnings


class Internet:
	def __init__(
			self, id=0, cache=None, expire_in=None, num_request_tries=4, rate_limit_wait_seconds=0.001,
			headers=None, parameters=None
	):
		if cache is None:
			self._cache = Cache(path='internet_cache')
		elif isinstance(cache, str):
			self._cache = Cache(path=cache)
		elif isinstance(cache, Cache):
			self._cache = cache
		elif cache == False:
			self._cache = None

		self._expire_in = expire_in
		self._id = id
		self._num_request_tries = num_request_tries
		self._rate_limit_wait = rate_limit_wait_seconds
		self._headers = headers
		self._parameters = parameters

	def _create_cached_functions(self):
		if self.cache:
			self.request = self.cache.make_cached(
				id=f'{self._id}_request',
				function=self._request,
				sub_directory=f'{self._id}_request',
				expire_in=self._expire_in
			)
		else:
			self.request = self._request

	@property
	def cache(self):
		"""
		:rtype: NoneType or Cache
		"""
		return self._cache

	def _request(self, url, verify=False, headers=None, parameters=None):
		headers = headers or self._headers
		parameters = parameters or self._parameters
		error = None
		for i in range(self._num_request_tries):
			if i > 0:
				sleep(0.001 * 10 ** (i-1))
			try:
				if self._rate_limit_wait and self._rate_limit_last_call:
					wait_time = self._rate_limit_wait - get_elapsed(start=self._rate_limit_last_call, unit='s')
					if wait_time > 0:
						sleep(wait_time)
				with warnings.catch_warnings():
					warnings.simplefilter('ignore')
					result = requests.get(url, params=parameters, headers=headers, verify=verify)
				break
			except SSLError as caught_error:
				print(f'try {i + 1}, error with get request with url="{url}"')
				warnings.warn(str(caught_error))
				error = caught_error
		else:
			print(f'failed after {self._num_request_tries} requests!')
			if error is None:
				raise RuntimeError(f'failed after {self._num_request_tries} requests!')
			else:
				raise error

		if self._rate_limit_wait:
			self._rate_limit_last_call = get_now()

		return result



