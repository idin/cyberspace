from bs4 import Tag
from .clone_beautiful_soup_tag import clone_beautiful_soup_tag
from .find_links import find_links

def find_unique(element, **kwargs):
	"""
	:type element: Tag
	:rtype: list
	"""
	element_copy = clone_beautiful_soup_tag(element)
	result = []
	first_child = element_copy.find(**kwargs)
	while first_child:
		result.append(first_child)
		first_child.extract()
		first_child = element_copy.find(**kwargs)
	return result


def _find_unique(element, **kwargs):
	try:
		found = element.find_all(recursive=False, **kwargs)
	except AttributeError:
		return []
	if found:
		if isinstance(found, list):
			try:
				children = element.children
				return [find_unique(child, **kwargs) for child in children]
			except AttributeError:
				return found
		else:
			return []
	else:
		result = []
		try:
			children = element.children
		except AttributeError:
			return []
		for child in children:
			result += find_unique(child, **kwargs)
		return result


def get_items(element, links_only=False, base=None):
	#items = element.find_all('li', recursive=False)
	items = find_unique(element=element, name='li')
	results = [get_lists(i, links_only=links_only, base=base) for i in items]
	return [x for x in results if x is not None]


def get_lists(element, links_only=False, base=None):
	if element.find('ul'):
		#lists = element.find_all('ul')
		lists = find_unique(element=element, name='ul')
		return [get_items(l, links_only=links_only, base=base) for l in lists]
	else:
		if links_only:
			return find_links(element=element, base=base)
		else:
			return element



