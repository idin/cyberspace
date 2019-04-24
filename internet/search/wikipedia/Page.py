from bs4 import BeautifulSoup
from pensieve import Pensieve

from .exceptions import PageError, RedirectError, DisambiguationError, ODD_ERROR_MESSAGE


class Page:
	def __init__(self, api=None, id=None, title=None, namespace=None, redirect=True, redirected_from=None):
		self._api = api
		self._pensieve = Pensieve(safe=True)
		if id or title:
			pass
		else:
			raise ValueError('Either id or title should be given!')

		self.pensieve.store('original_id', content=id)
		self.pensieve.store('original_title', content=title)
		self.pensieve.store('namespace', content=namespace)
		self.pensieve.store('redirect', content=redirect)
		self.pensieve.store('redirected_from', content=redirected_from)
		self._loaded = False

	@property
	def pensieve(self):
		"""
		:rtype: Pensieve
		"""
		return self._pensieve

	def clear(self):
		new_pensieve = Pensieve(safe=True)
		for key in ['original_id', 'original_title', 'namespace', 'redirect', 'redirected_from']:
			new_pensieve.store(key=key, content=self.pensieve[key])
		self._pensieve = new_pensieve

	@staticmethod
	def _get_state_attributes():
		return ['_loaded', '_pensievea']

	def __getstate__(self):
		return {name: getattr(self, name) for name in self._get_state_attributes()}

	def __setstate__(self, state):
		for name in self._get_state_attributes():
			setattr(self, name, state[name])
		self._api = None

	@property
	def title(self):
		if 'title' in self.pensieve:
			return self.pensieve['title']
		else:
			return self.pensieve['original_title']

	@property
	def id(self):
		if 'id' in self.pensieve:
			return self.pensieve['id']
		else:
			return self.pensieve['original_id']

	def __str__(self):
		return f'Wikipedia Page: {self.title} (id:{self.id})'

	def __repr__(self):
		return str(self)

	@property
	def api(self):
		"""
		:rtype: .Wikipedia.Wikipedia
		"""
		if self._api is None:
			raise AttributeError('Wikipedia API is missing!')
		else:
			return self._api

	@api.setter
	def api(self, api):
		self._api = api

	@staticmethod
	def get_search_parameters(id, title):
		query_parameters = {
			'prop': 'info|pageprops',
			'inprop': 'url',
			'ppprop': 'disambiguation',
			'redirects': '',
		}

		if id:
			query_parameters['pageids'] = id
		else:
			query_parameters['titles'] = title

		return query_parameters

	@staticmethod
	def get_html_parameters(id, title):
		query_params = {
			'prop': 'revisions',
			'rvprop': 'content',
			'rvparse': '',
			'rvlimit': 1
		}
		if id:
			query_params['pageids'] = id
		else:
			query_params['titles'] = title
		return query_params

	@staticmethod
	def get_summary_parameters(id, title):
		query_params = {
			'prop': 'extracts',
			'explaintext': '',
			'exintro': '',
		}
		if id:
			query_params['pageids'] = id
		else:
			query_params['titles'] = title
		return query_params

	@staticmethod
	def get_content_parameters(id, title):
		query_params = {
			'prop': 'extracts|revisions',
			'explaintext': '',
			'rvprop': 'ids'
		}
		if id:
			query_params['pageids'] = id
		else:
			query_params['titles'] = title

		return query_params

	def search_page(self, id, title, redirect, redirected_from, num_recursions=0):
		if num_recursions > 3:
			raise RecursionError()
		print(dict(title=title, id=id, redirect=redirect, redirected_from=redirected_from, num_recursions=num_recursions))

		search_query_parameters = self.get_search_parameters(id=id, title=title)
		search_request = self.api.request(search_query_parameters)

		query = search_request['query']
		id = list(query['pages'].keys())[0]
		page = query['pages'][id]

		# missing is present if the page is missing

		if 'missing' in page:
			raise PageError(id=id, title=title)

		# same thing for redirect, except it shows up in query instead of page for
		# whatever silly reason
		elif 'redirects' in query:
			if redirect:
				redirects = query['redirects'][0]

				if 'normalized' in query:
					normalized = query['normalized'][0]
					assert normalized['from'] == self.title, ODD_ERROR_MESSAGE

					from_title = normalized['to']

				else:
					from_title = self.title

				assert redirects['from'] == from_title, ODD_ERROR_MESSAGE

				# change the title and reload the whole object

				return self.search_page(
					id=id, title=redirects['to'],
					redirect=redirect, redirected_from=redirects['from'],
					num_recursions=num_recursions+1
				)
			else:
				raise RedirectError(getattr(self, 'title', page['title']))

		# since we only asked for disambiguation in ppprop,
		# if a pageprop is returned,
		# then the page must be a disambiguation page
		elif 'pageprops' in page:
			raise DisambiguationError(title=title, may_refer_to=['poof'])

		else:
			return {'id': str(id), 'title': title, 'page': page, 'redirected_from': redirected_from}



	def load(self):



		self.pensieve.store(
			key='search_result', precursors=['original_title', 'original_id', 'redirect'],
			function=lambda x: self.search_page(
				title=x['original_title'], id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)

		for key in ['id', 'title', 'page', 'redirected_from']:
			self.pensieve.store(key, precursors=['search_result'], function=lambda x: x[key])
		self.pensieve.store(key='url', precursors=['page'], function=lambda x: x['fullurl'], evaluate=False)

		self.pensieve.store(
			key='html', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self.get_html(id=x['id'], title=x['title'])
		)

		self.pensieve.store(
			key='parsed_html', precursors=['html'], evaluate=False,
			function=lambda x: BeautifulSoup(x, 'html.parser')
		)

		self.pensieve.store(
			key='links', precursors=['parsed_html'], evaluate=False,
			function=lambda x: self.get_links(x)
		)

		self.pensieve.store(
			key='summary', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self.get_summary(id=x['id'], title=x['title'])
		)

		self.pensieve.store(
			key='content', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self.get_content(id=x['id'], title=x['title'])
		)

		self.pensieve.store(
			key='extract', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['extract']
		)

		self.pensieve.store(
			key='revision_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['revid']
		)

		self.pensieve.store(
			key='parent_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['parentid']
		)

		self._loaded = True

	@property
	def url(self):
		if not self._loaded:
			self.load()
		return self.pensieve['url']

	@property
	def html_request(self):
		if not self._loaded:
			self.load()
		return self.pensieve['html_request']

	def get_html(self, id, title):
		html_query_parameters = self.get_html_parameters(id=id, title=title)
		html_request = self.api.request(html_query_parameters)
		return html_request['query']['pages'][id]['revisions'][0]['*']

	def get_links(self, parsed_html):
		links = parsed_html.find_all('li')
		filtered_links = [
			{'link': li, 'text': li.a.get_text() if li.a else None}
			for li in links if 'tocsection' not in ''.join(li.get('class', []))
		]
		return filtered_links

	def get_summary(self, id, title):
		summary_query_parameters = self.get_summary_parameters(id=id, title=title)
		summary_request = self.api.request(summary_query_parameters)
		return summary_request['query']['pages'][id]['extract']

	def get_content(self, id, title):
		content_parameters = self.get_content_parameters(id=id, title=title)
		content_request = self.api.request(content_parameters)
		return content_request['query']['pages'][id]

	@property
	def html(self):
		if not self._loaded:
			self.load()
		return self.pensieve['html']

	@property
	def links(self):
		if not self._loaded:
			self.load()
		return self.pensieve['links']

	@property
	def summary(self):
		if not self._loaded:
			self.load()
		return self.pensieve['summary']

	@property
	def content(self):
		if not self._loaded:
			self.load()
		return self.pensieve['content']

	@property
	def extract(self):
		if not self._loaded:
			self.load()
		return self.pensieve['extract']

	@property
	def revision_id(self):
		if not self._loaded:
			self.load()
		return self.pensieve['revision_id']

	@property
	def parent_id(self):
		if not self._loaded:
			self.load()
		return self.pensieve['parent_id']
