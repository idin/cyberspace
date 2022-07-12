import json
from soupspoon import separate_row_header, parse_link, find_links


import re

WORD = re.compile(r'\w+')


def tokenize(text):
	"""
	this function tokenizes text at a very high speed
	:param str text: text to be tokenized
	:rtype: list[str]
	"""
	words = WORD.findall(text)
	return words


class InfoBox:
	def __init__(self, html, extract=False, base_url=None):
		#strainer = SoupStrainer('table', {'class': re.compile('infobox.+vcard')})
		self._html = html
		self._extract = extract
		self._base = base_url
		self._dictionary = None
		self._links = None

	@property
	def dictionary(self):
		if self._dictionary is None:
			if self._html:
				for br in self._html.find_all('br'):
					br.replace_with('\n')
				self._dictionary = self._parse_table(self._html)
				if self._extract:
					self._prepare_links()
					self._html.extract()
			else:
				self._dictionary = {}
		return self._dictionary

	def __str__(self):
		return '\n'.join([f'{k}: {v}' for k, v in self.dictionary.items()])

	def __repr__(self):
		return 'InfoBox:\n'+str(self)

	def __getstate__(self):
		return {'html': self._html, 'extract': self._extract, 'dictionary': self._dictionary}

	def __setstate__(self, state):
		for name, value in state.items:
			setattr(self, f'_{name}', value)

	def __getitem__(self, item):
		return self.dictionary[item]

	def __contains__(self, item):
		return item in self.dictionary

	def copy(self):
		duplicate = self.__class__(html=None)
		duplicate._extract = self._extract
		duplicate._html = self._html
		if self._dictionary is not None:
			duplicate._dictionary = self._dictionary.copy()
		else:
			duplicate._dictionary = None
		return duplicate

	@staticmethod
	def _parse_table(table):
		result = {}
		title_number = 1
		unknown_header_number = 1

		for row in table.find_all('tr'):
			header, rest = separate_row_header(row)

			texts = ['_'.join(tokenize(text)) for text in rest.text.split('\n') if text != '']
			links = [parse_link(link) for link in rest.find_all('a')]

			if len(texts) > 0 or len(links) > 0:
				if header:
					header_text = '_'.join(tokenize(header.text))
				else:
					header_text = f'unknown_row_{unknown_header_number}'
					unknown_header_number += 1

				if header_text in result:
					result[header_text]['texts'] += texts
					result[header_text]['links'] += links
				else:
					result[header_text] = {'texts': texts, 'links': links}
			elif header:
				result[f'title_{title_number}'] = '_'.join(tokenize(header.text))
				title_number += 1

		return result

	def items(self):
		return self._dictionary.items()

	def keys(self):
		return self._dictionary.keys()

	def values(self):
		return self._dictionary.values()

	def _prepare_links(self):
		self._links = find_links(elements=self._html, base=self._base, ignore_anchors=True)

	@property
	def links(self):
		if self._links is None:
			self._prepare_links()
		return self._links



