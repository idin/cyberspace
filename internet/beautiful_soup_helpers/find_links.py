from .clean_html_text import clean_html_text


class Link:
	def __init__(self, element, base=None):
		a = element.find('a')
		if a:
			element = a
		self._element = element
		self._url = self.get_url(element=element, base=base)
		self._text = False

	def __str__(self):
		return f'{self.text} {self.url}'

	def __repr__(self):
		return str(self)

	def is_anchor(self):
		return self._url.startswith('#')

	@property
	def text(self):
		if self._text == False:
			self._text = self.get_text(element=self._element) or self._url
		return self._text

	@property
	def url(self):
		return self._url

	def get_url(self, element, base=None):
		try:
			href = element['href']
		except KeyError:
			raise TypeError('element does not have a url!')

		if href.startswith('http://') or href.startswith('https://') or base is None or href.startswith('#'):
			return href
		elif href.startswith('/'):
			if base is None:
				raise TypeError('no base is provided!')
			else:
				return base + href

	def get_text(self, element):
		try:
			return clean_html_text(html=element, replace_images=True)
		except AttributeError:
			return None

def parse_link(element, base=None):
	try:
		link = Link(element=element, base=base)
		if link.is_anchor():
			return clean_html_text(html=element, replace_images=True)
		else:
			return link
	except TypeError:
		return clean_html_text(html=element, replace_images=True)

def find_links(element, base):
	links = element.find_all('a')
	if links is not None:
		result = [parse_link(element=link, base=base) for link in links]
		return [x for x in result if x]
	else:
		return []
