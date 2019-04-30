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

	def request(self, parameters=None, url=None, format='json'):
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
