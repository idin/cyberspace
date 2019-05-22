from linguistics import tokenize
from bs4 import BeautifulSoup


def get_paragraphs_by_tokens(soup, num_tokens=100):
	"""
	:param BeautifulSoup soup: BeautifulSoup
	:param int num_tokens: number of tokens required to finish the job
	:rtype: list[str]
	"""
	_paragraphs = soup.find_all('p')
	paragraphs = []
	tokens = []
	for paragraph in _paragraphs:
		if len(tokens) >= num_tokens:
			break

		paragraphs.append(paragraph)
		tokens += tokenize(paragraph.text)
	return {'paragraphs': paragraphs, 'tokens': tokens}