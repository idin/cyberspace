from bs4 import Tag
import re


def get_wikipedia_id(url_response):
	"""
	:type element: Tag
	:rtype: int
	"""
	keyword = '"wgArticleId"'
	text = url_response
	if keyword in text:
		beginning = text[text.find(keyword) + len(keyword):]
		ending = beginning[:beginning.find(',')]
		ints = re.findall('\d+', ending)
		if len(ints) > 0:
			return int(ints[0])

def get_page_title(url_response):
	"""
	:type element: Tag
	:rtype: int
	"""
	keyword = '"wgTitle"'
	text = url_response
	if keyword in text:
		beginning = text[text.find(keyword) + len(keyword):]
		ending = beginning[:beginning.find(',')]
		results = re.findall('".+"', ending)
		if len(results) > 0:
			return results[0][1:-1]

def get_page_language(url_response):
	"""
	:type element: Tag
	:rtype: int
	"""
	keyword = '"wgPageContentLanguage"'
	text = url_response
	if keyword in text:
		beginning = text[text.find(keyword) + len(keyword):]
		ending = beginning[:beginning.find(',')]
		results = re.findall('".+"', ending)
		if len(results) > 0:
			return results[0][1:-1]

def get_page_namespace(url_response):
	"""
	:type element: Tag
	:rtype: int
	"""
	keyword = '"wgNamespaceNumber"'
	text = url_response
	if keyword in text:
		beginning = text[text.find(keyword) + len(keyword):]
		ending = beginning[:beginning.find(',')]
		ints = re.findall('\d+', ending)
		if len(ints) > 0:
			return int(ints[0])
