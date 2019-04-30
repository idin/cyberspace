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