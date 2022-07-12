from disk import Path


class WikipediaMemory:
	def __init__(self, path):
		self._pages = {}

		self._dictionary = {
			'page_attributes': {},
			'n_items': 0,
			'request_results': {}
		}

		if path is None:
			self._path = None
		else:
			self._path = Path(path)
			if self._path.exists():
				self._dictionary = self._path.load(method='pickle')

	def save_to_file(self):
		if self._path.exists():
			self._path.delete()
		if self.n_items > 0:
			self._path.save(self._dictionary)

	def delete(self, key):
		del self._dictionary[key]

	def has_file(self):
		return self._path is not None

	def get_page(self, key):
		try:
			return self._pages[key]
		except KeyError:
			return False

	def set_page(self, key, page):
		self._pages[key] = page

	@property
	def page_attributes(self):
		return self._dictionary['page_attributes']

	@property
	def n_items(self):
		return self._dictionary['n_items']

	@property
	def request_results(self):
		return self._dictionary['request_results']

	def get_page_attribute(self, url, attribute):
		try:
			return self.page_attributes[url][attribute]
		except KeyError:
			return False

	def set_page_attribute(self, url, attribute, value):
		if url not in self.page_attributes:
			self.page_attributes[url] = {}

		self.page_attributes[url][attribute] = value
		self._dictionary['n_items'] += 1

	def get_request_result(self, key):
		try:
			return self.request_results[key]
		except KeyError:
			return False

	def set_request_result(self, key, results):
		self.request_results[key] = results
