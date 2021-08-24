from .. import Scraper
from ravenclaw import standardize_columns
from pandas import DataFrame
from silverware import read_table


class Country:
	def __init__(self, name, alpha_2, alpha_3, numeric):
		self._dictionary = {
			'name': name,
			'alpha_2': alpha_2,
			'alpha_3': alpha_3,
			'numeric': numeric
		}

	def __getstate__(self):
		return self._dictionary

	def __setstate__(self, state):
		self._dictionary = state

	@property
	def name(self):
		return self._dictionary['name']

	@property
	def alpha_2(self):
		return self._dictionary['alpha_2']

	@property
	def alpha_3(self):
		return self._dictionary['alpha_3']

	@property
	def numeric(self):
		return self._dictionary['numeric']

	def get(self, key):
		return self._dictionary[key]

	def __eq__(self, other):
		return self.alpha_3 == other.alpha_3

	def __lt__(self, other):
		return self.name < other.name

	def __gt__(self, other):
		return self.name > other.name

	def __le__(self, other):
		return not (self > other)

	def __ge__(self, other):
		return not (self < other)

	def __ne__(self, other):
		return not (self == other)


class CountryCodes(Scraper):
	def __init__(self, rate_limit_wait_seconds=0.01, cache=None, num_request_tries=4):
		self._table = None
		self._countries = None
		super().__init__(
			name='country_codes', expire_in='1 year', rate_limit_wait_seconds=rate_limit_wait_seconds,
			cache=cache, num_request_tries=num_request_tries
		)

	def _create_cached_functions(self):
		super()._create_cached_functions()
		if self.cache:
			self.get_table = self.cache.make_cached(
				id='iban_country_codes_get_table',
				function=self._get_table,
				sub_directory='iban_cc_table',
				expire_in='1 year'
			)
		else:
			self.get_table = self._get_table

	def _get_state_attribute_names(self):
		return super()._get_state_attribute_names() + ['_table', '_countries']

	def _get_table(self):
		"""
		:rtype: DataFrame
		"""
		soup = self.get_soup(url='https://www.iban.com/country-codes')
		return standardize_columns(data=read_table(table=soup.find(name='table'))).rename(
			columns={'country': 'name', 'alpha_2_code': 'alpha_2', 'alpha_3_code': 'alpha_3'}
		)

	@property
	def table(self):
		"""
		:rtype: DataFrame
		"""
		if self._table is None:
			self._table = self.get_table()
		return self._table

	@property
	def countries(self):
		"""
		:rtype: dict[str, Country]
		"""
		if self._countries is None:
			data = self.table.copy()
			countries = data.apply(
				func=lambda row: Country(
					name=row['name'], alpha_2=row['alpha_2'], alpha_3=row['alpha_3'], numeric=row['numeric']
				),
				axis=1
			)
			self._countries = {
				getattr(country, attribute): country
				for country in countries
				for attribute in ['name', 'alpha_2', 'alpha_3', 'numeric']
			}
		return self._countries

	def convert(self, code, to='alpha_3'):
		return self.countries[code].get(key=to)
