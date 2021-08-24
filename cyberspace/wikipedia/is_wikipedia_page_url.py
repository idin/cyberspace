import re


def is_wikipedia_page_url(url):
	wikipedia_url_regex_str = '^(http|https)://.+\.wikipedia.org/'
	wikipedia_url_regex = re.compile(wikipedia_url_regex_str)
	if re.match(wikipedia_url_regex, url):
		return True
	else:
		return False


def is_mobile_wikipedia_page_url(url):
	wikipedia_url_regex_str = '^(http|https)://.+\./m\.wikipedia.org/'
	wikipedia_url_regex = re.compile(wikipedia_url_regex_str)
	if re.match(wikipedia_url_regex, url):
		return True
	else:
		return False


def convert_mobile_wikipedia_page_url_to_normal_page(url):
	return url.replace('.m.wikipedia.org', '.wikipedia.org')
