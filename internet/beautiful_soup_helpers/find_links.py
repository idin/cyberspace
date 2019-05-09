def parse_link(link, base=None):
	result = {}

	try:
		href = link['href']
		if 'http:' in href or 'https:' in href or base is None or href.startswith('#'):
			result['url'] = href
		else:
			result['url'] = (base + href)
	except KeyError:
		return None

	try:
		text = link.text
		if text:
			if len(text) > 0:
				result['text'] = link.text
	except AttributeError:
		pass
	return result


def find_links(element, base):
	links = element.find_all('a')
	if links is not None:
		result = [parse_link(link=link, base=base) for link in links]
		return [x for x in result if x]
	else:
		return []