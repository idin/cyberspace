from .clone_beautiful_soup_tag import clone_beautiful_soup_tag


def separate_row_header(row):
	row = clone_beautiful_soup_tag(row)
	header = row.find('th')
	if header:
		header_clone = clone_beautiful_soup_tag(header)
		header.decompose()
		return header_clone, row
	else:
		return header, row

def separate_row_headers(table):
	"""
	:param table:
	:rtype: list
	"""
	return [separate_row_header(row) for row in table.find_all('tr')]

def parse_link(link):
	result = {}
	try:
		result['title'] = link['title']
	except KeyError:
		pass

	try:
		result['url'] = link['href']
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
