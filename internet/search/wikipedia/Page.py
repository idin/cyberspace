from bs4 import BeautifulSoup, SoupStrainer
from pensieve import Pensieve
import re
import datefinder

from .exceptions import PageError, RedirectError, DisambiguationError, ODD_ERROR_MESSAGE
from .Subject import InfoBox


class Page:
	def __init__(self, api=None, id=None, title=None, namespace=None, redirect=True, redirected_from=None):
		self._api = api
		self._pensieve = Pensieve(safe=True)
		if id or title:
			pass
		else:
			raise ValueError('Either id or title should be given!')

		self._pensieve.store('original_id', content=id)
		self._pensieve.store('original_title', content=title)
		self._pensieve.store('namespace', content=namespace)
		self._pensieve.store('redirect', content=redirect)
		self._pensieve.store('redirected_from', content=redirected_from)
		self._loaded = False

	@property
	def pensieve(self):
		"""
		:rtype: Pensieve
		"""
		if not self._loaded:
			self.load()
		return self._pensieve

	@property
	def base_url(self):
		return 'http://' + self.api.language + '.wikipedia.org'

	def clear(self):
		new_pensieve = Pensieve(safe=True)
		for key in ['original_id', 'original_title', 'namespace', 'redirect', 'redirected_from']:
			new_pensieve.store(key=key, content=self.pensieve[key])
		self._pensieve = new_pensieve
		self._loaded = False

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
		if 'title' in self._pensieve:
			return self._pensieve['title']
		else:
			return self._pensieve['original_title']

	@property
	def id(self):
		if 'id' in self._pensieve:
			return self._pensieve['id']
		else:
			return self._pensieve['original_id']

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
		"""
		:type api: .Wikipedia.Wikipedia
		"""
		self._api = api

	def request(self, url=None, parameters=None, format='html'):
		return self.api.request(url=url, parameters=parameters, format=format)

	@staticmethod
	def _get_search_parameters(id, title):
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
	def _get_html_parameters(id, title):
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
	def _get_summary_parameters(id, title):
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
	def _get_content_parameters(id, title):
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

	def _search_page(self, id, title, redirect, redirected_from, num_recursions=0):
		if num_recursions > 3:
			raise RecursionError()
		# print(dict(title=title, id=id, redirect=redirect, redirected_from=redirected_from, num_recursions=num_recursions))

		search_query_parameters = self._get_search_parameters(id=id, title=title)
		search_request = self.request(parameters=search_query_parameters, format='json')

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

				return self._search_page(
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
		self._pensieve.store(
			key='search_result', precursors=['original_title', 'original_id', 'redirect'],
			function=lambda x: self._search_page(
				title=x['original_title'], id=x['original_id'], redirect=x['redirect'],
				redirected_from=None
			)
		)

		for key in ['id', 'title', 'page', 'redirected_from']:
			self._pensieve.store(key, precursors=['search_result'], function=lambda x: x[key])
		self._pensieve.store(key='url', precursors=['page'], function=lambda x: x['fullurl'], evaluate=False)

		self._pensieve.store(
			key='json', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_json(id=x['id'], title=x['title'])
		)

		'''
		self._pensieve.store(
			key='parsed_json', precursors=['json'], evaluate=False,
			function=lambda x: BeautifulSoup(x, 'lxml')
		)
		'''

		self._pensieve.store(
			key='url_response', precursors=['url'],
			function=lambda x: self.request(url=x, format='response'), evaluate=False
		)

		self._pensieve.store(
			key='parsed_html', precursors=['url_response'], evaluate=False,
			function=lambda x: BeautifulSoup(x.text, 'lxml')
		)

		self._pensieve.store(
			key='links', precursors=['parsed_html'], evaluate=False,
			function=lambda x: self._get_links(x)
		)

		self._pensieve.store(
			key='summary', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_summary(id=x['id'], title=x['title'])
		)

		self._pensieve.store(
			key='content', precursors=['id', 'title'], evaluate=False,
			function=lambda x: self._get_content(id=x['id'], title=x['title'])
		)

		self._pensieve.store(
			key='extract', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['extract']
		)

		self._pensieve.store(
			key='revision_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['revid']
		)

		self._pensieve.store(
			key='parent_id', precursors=['content'], evaluate=False, materialize=False,
			function=lambda x: x['revisions'][0]['parentid']
		)

		'''
		self._pensieve.store(
			key='info_box', precursors=['parsed_html'], evaluate=False, materialize=False,
			function=lambda x: x.find('table', {'class': re.compile('infobox.+vcard')})
		)
		'''

		self._pensieve.store(
			key='info_box', precursors=['url_response'], evaluate=False, materialize=True,
			function=lambda x: InfoBox(html=x.text)
		)

		# # # Persons:

		self._pensieve.store(
			key='birthdate', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_date_in_info_box(info_box=x, label='born')
		)

		self._pensieve.store(
			key='deathdate', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_date_in_info_box(info_box=x, label='died')
		)

		self._pensieve.store(
			key='occupation', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_in_info_box(info_box=x, label='occupation')
		)

		# # # Companies

		self._pensieve.store(
			key='ticker', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_in_info_box(info_box=x, label='traded as')[0].text
		)

		self._pensieve.store(
			key='isin', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_links_in_info_box(info_box=x, label='isin')
		)

		self._pensieve.store(
			key='founders', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_links_in_info_box(info_box=x, label='founders')
		)

		self._pensieve.store(
			key='founded', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_date_in_info_box(info_box=x, label='founded')
		)

		self._pensieve.store(
			key='industry', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_links_in_info_box(info_box=x, label='industry')
		)

		self._pensieve.store(
			key='headquarters', precursors=['info_box'], evaluate=False, materialize=True,
			function=lambda x: self._find_in_info_box(info_box=x, label='headquarters')[0].text
		)

		self._loaded = True

	def _get_json(self, id, title):
		html_query_parameters = self._get_html_parameters(id=id, title=title)
		html_request = self.request(parameters=html_query_parameters, format='json')
		return html_request['query']['pages'][id]['revisions'][0]['*']

	@staticmethod
	def _get_subject(html):
		return Subject(html)


	@staticmethod
	def _get_links(parsed_html):
		links = parsed_html.find_all('li')
		filtered_links = [
			{'link': li, 'text': li.a.get_text() if li.a else None}
			for li in links if 'tocsection' not in ''.join(li.get('class', []))
		]
		return filtered_links

	def _get_summary(self, id, title):
		summary_query_parameters = self._get_summary_parameters(id=id, title=title)
		summary_request = self.request(parameters=summary_query_parameters)
		return summary_request['query']['pages'][id]['extract']

	def _get_content(self, id, title):
		content_parameters = self._get_content_parameters(id=id, title=title)
		content_request = self.request(parameters=content_parameters)
		return content_request['query']['pages'][id]

	@staticmethod
	def _find_in_info_box(info_box, label):
		def __get_th_text(tr):
			try:
				return tr.find('th').text.lower()
			except:
				return ''

		return [tr for tr in info_box.find_all('tr') if label in __get_th_text(tr=tr)]

	@classmethod
	def _find_links_in_info_box(cls, info_box, label):
		trs = cls._find_in_info_box(info_box=info_box, label=label)
		return [{'link': link.get('href'), 'text': link.get_text()} for tr in trs for link in tr.find_all('a')]

	@classmethod
	def _find_date_in_info_box(cls, info_box, label):
		trs = cls._find_in_info_box(info_box=info_box, label=label)
		dates = [date for tr in trs for date in datefinder.find_dates(tr.text)]
		if len(dates) > 0:
			return dates[0]
		else:
			return None

	def __getitem__(self, item):
		return self.pensieve[item]
