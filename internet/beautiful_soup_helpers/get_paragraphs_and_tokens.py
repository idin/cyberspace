from linguistics import tokenize
from bs4 import BeautifulSoup


def get_paragraphs_and_tokens(soup, num_tokens=100, min_length=2):
	"""
	:param BeautifulSoup soup: BeautifulSoup
	:param int num_tokens: number of tokens required to finish the job
	:param int min_length: minimum length for a token to be considered (anything shorter will be ignored)
	:rtype: list[str]
	"""
	_paragraphs = soup.find_all('p')
	paragraphs = []
	tokens = []
	for paragraph in _paragraphs:
		if len(tokens) >= num_tokens:
			break

		paragraphs.append(paragraph)
		tokens += [token for token in tokenize(paragraph.text) if len(token) >= min_length]
	return {'paragraphs': paragraphs, 'tokens': tokens}