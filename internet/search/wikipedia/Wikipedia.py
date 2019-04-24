import requests
from chronology import get_now, get_elapsed_seconds
import time

from .exceptions import HTTPTimeoutError, WikipediaException
from .Page import Page


class Wikipedia:
	def __init__(
			self, language='en',
			user_agent='wikipedia (https://github.com/goldsmith/Wikipedia/)',
			rate_limit_wait_seconds=0.01
	):
		self._language = language
		self._user_agent = user_agent
		self._rate_limit_wait = rate_limit_wait_seconds
		self._rate_limit_last_call = None

	@property
	def language(self):
		return self._language.lower()

	@property
	def api_url(self):
		return 'http://' + self.language + '.wikipedia.org/w/api.php'

	def request(self, params):
		"""
		:type params: dict
		:rtype: dict
		"""
		params['format'] = 'json'
		if 'action' not in params:
			params['action'] = 'query'

		headers = {'User-Agent': self._user_agent}

		if self._rate_limit_wait and self._rate_limit_last_call:
			wait_time = self._rate_limit_wait - get_elapsed_seconds(start=self._rate_limit_last_call, end=get_now())
			if  wait_time > 0:
				time.sleep(wait_time)

		r = requests.get(self.api_url, params=params, headers=headers)
		if self._rate_limit_wait:
			self._rate_limit_last_call = get_now()

		return r.json()

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
		return [Page(id=d['pageid'], title=d['title'], namespace=d['ns'], api=self, redirect=redirect) for d in results]
