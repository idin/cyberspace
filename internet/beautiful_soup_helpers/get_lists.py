from bs4 import Tag
from .clone_beautiful_soup_tag import clone_beautiful_soup_tag
from .parse_link import parse_link


def get_items(element, **kwargs):
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


def get_lists(element, links_only=False, base=None):
	"""
	:type element: Tag
	:rtype: list
	"""
	result = get_items(element=element, name='ul')
	if links_only:
		return [
			get_items_in_list(x, links_only=links_only, base=base) if x.find('li') else [
				parse_link(link, base=base) for link in x.find_all('a') or []
			]
			for x in result
		]
	else:
		return [get_items_in_list(x, links_only=links_only) if x.find('li') else x.contents for x in result]


def get_items_in_list(element, links_only=False, base=None):
	"""
	:type element: Tag
	:rtype: list
	"""
	result = get_items(element=element, name='li')
	if links_only:
		return [
			get_lists(x, links_only=links_only, base=base) if x.find(name='ul') else [
				parse_link(link, base=base) for link in x.find_all('a') or []
			]
			for x in result
		]
	else:
		return [get_lists(x, links_only=links_only) if x.find(name='ul') else x.contents for x in result]

