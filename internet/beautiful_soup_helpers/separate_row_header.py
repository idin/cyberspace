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
