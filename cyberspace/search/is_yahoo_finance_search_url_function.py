import re

def is_yahoo_finance_search_url(url):
	regex_str = '^(http|https)://finance.search.yahoo.com'
	regex = re.compile(regex_str)
	if re.match(regex, url):
		return True
	else:
		return False