from ..beautiful_soup_helpers import find_links, clone_beautiful_soup_tag, Link

from collections import Counter
from bs4 import BeautifulSoup
from linguistics.english import get_stop_words


def get_search_parameters(id, title):
	query_parameters = {
		'prop': 'info|pageprops',
		'inprop': 'url',
		'ppprop': 'disambiguation',
		'redirects': '',
	}

	if id:
		query_parameters['pageids'] = id
	else:
		query_parameters['titles'] = title

	return query_parameters


def get_disambiguation_results(disambiguation, html, base_url):
	if disambiguation:
		original_content = html.find(attrs={'id': 'bodyContent'}).find(attrs={'id': 'mw-content-text'})
		content = clone_beautiful_soup_tag(element=original_content)
		disambigbox = content.find(attrs={'id': 'disambigbox'})
		if disambigbox:
			disambigbox.extract()
		printfooter = content.find(attrs={'class': 'printfooter'})
		if printfooter:
			printfooter.extract()
		links = find_links(element=content, base=base_url)
		return [link for link in links if '/index.php?' not in link.url]
	else:
		return []


def get_html_parameters(id, title):
	query_params = {
		'prop': 'revisions',
		'rvprop': 'content',
		'rvparse': '',
		'rvlimit': 1
	}
	if id:
		query_params['pageids'] = id
	else:
		query_params['titles'] = title
	return query_params


def get_summary_parameters(id, title):
	query_params = {
		'prop': 'extracts',
		'explaintext': '',
		'exintro': '',
	}
	if id:
		query_params['pageids'] = id
	else:
		query_params['titles'] = title
	return query_params


def get_page_summary(page, id, title):
	id = str(id)
	summary_query_parameters = get_summary_parameters(id=id, title=title)
	summary_request = page.request(parameters=summary_query_parameters, format='json')
	return summary_request['query']['pages'][id]['extract']


def get_content_parameters(id, title):
	query_params = {
		'prop': 'extracts|revisions',
		'explaintext': '',
		'rvprop': 'ids'
	}
	if id:
		query_params['pageids'] = id
	else:
		query_params['titles'] = title

	return query_params


def _depricated_separate_body_from_navigation_and_info_box(url_response):
	html = BeautifulSoup(url_response.text, 'lxml')

	vertical_navigation_box = html.find(name='table', attrs={'class': 'vertical-navbox'})
	info_box = html.find(name='table', attrs={'class': 'infobox'})
	navigation_boxes = html.find_all(name='div', attrs={'role': 'navigation'})
	categories = html.find(name='div', attrs={'id': 'catlinks'})


	result = {
		'body': html,
		'vertical_navigation_box': vertical_navigation_box,
		'info_box': info_box,
		'categories': categories,
		'navigation_boxes': navigation_boxes
	}

	if vertical_navigation_box:
		vertical_navigation_box.extract()
	if info_box:
		info_box.extract()
	for navigation_box in navigation_boxes:
		navigation_box.extract()
	if categories:
		categories.extract()


	return result


def get_categories(category_links):
	if isinstance(category_links, list):
		urls = [link.url for link in category_links if isinstance(link, Link)]
		category_sign = '/wiki/Category:'
		category_urls = [url for url in urls if category_sign in url]
		return [url[url.find(category_sign) + len(category_sign):] for url in category_urls]
	else:
		return []

_NONPRONOUN_SW = get_stop_words(include_pronoun_forms=False)
def get_page_signature(tokens, info_box, categories):

	lowercase_tokens = [str(token).lower() for token in tokens]
	token_list = [f'token:{token}' for token in lowercase_tokens if token not in _NONPRONOUN_SW]

	lowercase_info_list = [str(info).lower() for info in info_box.keys()]
	info_list = [f'info:{info}' for info in lowercase_info_list if info not in _NONPRONOUN_SW]

	lowercase_category_list = [str(category).lower() for category in categories]
	category_list = [f'category:{category}' for category in lowercase_category_list if category not in _NONPRONOUN_SW]

	signature = token_list + info_list + category_list

	return dict(Counter(signature))

def get_vertical_navigation_box(x, extract=False):
	result = x.find(name='table', attrs={'class': 'vertical-navbox'})
	if result is not None:
		if extract:
			result.extract()
	return result

def get_navigation_boxes(x, extract=False):
	boxes = x.find_all(name='div', attrs={'role': 'navigation'})
	result = []
	if boxes is not None:
		if extract:
			for box in boxes:
				result.append(box.extract())
	return result

def get_category_box(x, extract=False):
	result = x.find(name='div', attrs={'id': 'catlinks'})
	if result is not None:
		if extract:
			result.extract()
	return result
