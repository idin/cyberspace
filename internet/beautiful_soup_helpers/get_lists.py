from bs4 import Tag
from .clone_beautiful_soup_tag import clone_beautiful_soup_tag
from .find_links import parse_link, find_links


def find_all(element, **kwargs):
	"""
	:type element: Tag
	:rtype: list
	"""
	element_copy = clone_beautiful_soup_tag(element)
	result = []
	first_child = element_copy.find(**kwargs)
	while first_child:
		result.append(clone_beautiful_soup_tag(first_child))
		first_child.decompose()
		first_child = element_copy.find(**kwargs)
	return result


def get_items(list_element, links_only=False, base=None):
	items = find_all(element=list_element, name='li')
	results = [get_lists(i, links_only=links_only, base=base) for i in items]
	return [x for x in results if x is not None]


def get_lists(element, links_only=False, base=None):
	if element.find('ul'):
		lists = find_all(element=element, name='ul')
		return [get_items(l, links_only=links_only, base=base) for l in lists]
	else:
		if links_only:
			links = find_links(element=element, base=base)
			if len(links) == 0:
				return None
			elif len(links) == 1:
				return links[0]
			else:
				return links
		else:
			return element


