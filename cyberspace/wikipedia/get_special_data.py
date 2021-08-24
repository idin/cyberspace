from pensieve import Pensieve
from chronometry.progress import ProgressBar
from silverware import Link


def get_special_data(wikipedia, name, echo=1):
	"""
	:type wikipedia: .Wikipedia.Wikipedia
	:type name: str
	:rtype: list[Pensieve]
	"""
	if name == 'country_pages':
		page = wikipedia.get_page(url='https://en.wikipedia.org/wiki/List_of_national_capitals')
		countries = list(page['tables'][0]['country'])

		for one_or_more_links in countries:
			if isinstance(one_or_more_links, list):
				for link in one_or_more_links:
					if isinstance(link, Link):
						yield wikipedia.get_page(url=link.url)
			elif isinstance(one_or_more_links, Link):
				yield wikipedia.get_page(url=one_or_more_links.url)

	if name == 'country_capital_pages':
		page = wikipedia.get_page(url='https://en.wikipedia.org/wiki/List_of_national_capitals')
		capitals = list(page['tables'][0]['city'])

		for one_or_more_links in capitals:
			if isinstance(one_or_more_links, list):
				for link in one_or_more_links:
					if isinstance(link, Link):
						yield wikipedia.get_page(url=link.url)
			elif isinstance(one_or_more_links, Link):
				yield wikipedia.get_page(url=one_or_more_links.url)

	if name == 'countries':
		page = wikipedia.get_page(url='https://en.wikipedia.org/wiki/List_of_national_capitals')
		table = page['tables'][0]

		def row_to_pensieve(row):
			pensieve = Pensieve(safe=False, warn_unsafe=False)
			pensieve['capital'] = row['city'][0] if isinstance(row['city'], list) else row['city']
			pensieve['country'] = row['country'][0] if isinstance(row['country'], list) else row['country']
			pensieve.store(key='capital_name', precursors=['capital'], function=lambda x: x.text, evaluate=False)
			pensieve.store(
				key='capital_page', precursors=['capital'], function=lambda x: wikipedia.get_page(url=x.url), evaluate=False
			)
			pensieve.store(key='country_name', precursors=['country'], function=lambda x: x.text, evaluate=False)
			pensieve.store(
				key='country_page', precursors=['country'],
				function=lambda x: wikipedia.get_page(url=x.url), evaluate=False
			)
			return pensieve
		return list(ProgressBar.apply(function=row_to_pensieve, data=table, echo=echo))


