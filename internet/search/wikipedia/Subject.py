from bs4 import BeautifulSoup, SoupStrainer
import re
from ...beautiful_soup_helpers import separate_row_header, parse_link

class InfoBox:
	def __init__(self, html):
		strainer = SoupStrainer('table', {'class': re.compile('infobox.+vcard')})
		self._dictionary = self._parse_table(BeautifulSoup(html, 'lxml', parse_only=strainer))

	def __repr__(self):
		return str(self._dictionary)

	@staticmethod
	def _parse_table(table):
		result = {}
		title_number = 1
		unknown_header_number = 1
		for row in table.find_all('tr'):
			header, rest = separate_row_header(row)

			texts = [text.replace(u'\xa0', u' ') for text in rest.text.split('\n') if text != '']
			links = [parse_link(link) for link in rest.find_all('a')]

			if len(texts) > 0 or len(links) > 0:
				if header:
					header_text = header.text.replace(u'\xa0', u' ')
				else:
					header_text = f'unknown_row_{unknown_header_number}'
					unknown_header_number += 1

				if header_text in result:
					result[header_text]['texts'] += texts
					result[header_text]['links'] += links
				else:
					result[header_text] = {'texts': texts, 'links': links}
			elif header:
				result[f'title_{title_number}'] = header.text.replace(u'\xa0', u' ')
				title_number += 1

		return result

	def __getitem__(self, item):
		return self._dictionary[item]

	def __contains__(self, item):
		return item in self._dictionary
