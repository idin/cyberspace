import json
from silverware import separate_row_header, parse_link


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
	def __init__(self, html, extract=False):
		#strainer = SoupStrainer('table', {'class': re.compile('infobox.+vcard')})
		if html:
			for br in html.find_all('br'):
				br.replace_with('\n')
			self._dictionary = self._parse_table(html)
			if extract:
				html.extract()
		else:
			self._dictionary = {}

	def __str__(self):
		return '\n'.join([f'{k}: {v}' for k, v in self._dictionary.items()])

	def __repr__(self):
		return 'InfoBox:\n'+str(self)

	def __getstate__(self):
		return self._dictionary

	def __setstate__(self, state):
		self._dictionary = state

	def __getitem__(self, item):
		return self._dictionary[item]

	def __contains__(self, item):
		return item in self._dictionary

	def copy(self):
		duplicate = self.__class__(html=None)
		duplicate._dictionary = self._dictionary.copy()
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
