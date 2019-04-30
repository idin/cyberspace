def parse_link(link, base=None):
	result = {}

	try:
		href = link['href']
		if href.startswith('http') or base is None:
			result['url'] = href
		else:
			result['url'] = base + href
	except KeyError:
		pass

	try:
		text = link.text
		if text:
			if len(text) > 0:
				result['text'] = link.text
	except AttributeError:
		pass

	if len(result) > 0:
		return result
	else:
		return None


def find_links(element):
	result = element.find('a')
	if result is not None:
		return result
	else:
		return []