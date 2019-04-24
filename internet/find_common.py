def find_common_left(strings):
	"""
	:param list[str] strings: list of strings we want to find a common left part in
	:rtype: str
	"""
	length = min([len(s) for s in strings])
	i = 0
	result = ''
	for i in range(length):
		if all([strings[0][i] == s[i] for s in strings[1:]]):
			result += strings[0][i]
		else:
			break
	return result


def find_common_right(strings):
	reversed = [s[::-1] for s in strings]
	return find_common_left(reversed)[::-1]


def find_common(strings, side='left'):
	"""
	:param list[str] strings: list of strings we want to find a common left part in
	:rtype: str
	"""
	if side[0].lower() == 'l':
		return find_common_left(strings=strings)
	else:
		return find_common_right(strings=strings)
