def get_url(element, base=None):
	try:
		href = element.attrs['href']
		if href.startswith('http'):
			return href
		elif href.startswith('#'):
			return None
		elif base is None:
			return None
		else:
			return base + href
	except (KeyError, AttributeError):
		return None


def get_anchor(element):
	try:
		href = element['href']
		if href.startswith('#'):
			return href
		else:
			return None
	except (KeyError, AttributeError):
		return None


def break_lists(element):

	def _recursive_find(x, _result):
		lists = x.find_all('ul')
		if lists is None:
			final_list = x.extract()
			items = final_list.find_all('li')
			_result.append(items)
		else:
			print(len(lists))
			for x in lists:
				_recursive_find(x, _result)
	result = []
	_recursive_find(element, [])
	return result
