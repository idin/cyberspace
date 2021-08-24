from silverware import Spoon, Link, parse_link, find
from bs4 import BeautifulSoup, Tag


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
		content = Spoon.clone(soup=original_content, in_spoon=False)
		disambigbox = content.find(attrs={'id': 'disambigbox'})
		if disambigbox:
			disambigbox.extract()
		printfooter = content.find(attrs={'class': 'printfooter'})
		if printfooter:
			printfooter.extract()
		links = Spoon.find_links(element=content, base_url=base_url)
		return [link for link in links if hasattr(link, 'url') and '/index.php?' not in link.url]
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
	try:
		return summary_request['query']['pages'][id]['extract']
	except Exception as e:
		print('error with', page, id, title, sep='\n')
		raise e

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


def separate_body_from_navigation_and_info_box(url_response):
	html = BeautifulSoup(url_response.text, 'lxml')

	vertical_navigation_box = html.find(name='table', attrs={'class': 'vertical-navbox'})
	info_box = html.find(name='table', attrs={'class': 'infobox'})
	navigation_boxes = html.find_all(name='div', attrs={'role': 'navigation'})
	categories = html.find(name='div', attrs={'id': 'catlinks'})
	category_box = html.find(name='div', attrs={'id': 'catlinks'})
	external_links = html.find(name='span', attrs={'id': ['External_links', 'References', 'See_also', 'Notes_and_references']})
	if external_links:
		spoon = Spoon(soup=html).after(external_links)
		external_links = spoon.extract()

	result = {
		'body': html,
		'vertical_navigation_box': vertical_navigation_box,
		'info_box': info_box,
		'categories': categories,
		'navigation_boxes': navigation_boxes or [],
		'category_box': category_box,
		'external_links': external_links
	}

	if vertical_navigation_box:
		vertical_navigation_box.extract()
	if info_box:
		info_box.extract()
	for navigation_box in navigation_boxes:
		navigation_box.extract()
	if categories:
		categories.extract()
	if category_box:
		category_box.extract()

	return result


def get_categories(category_links):
	if isinstance(category_links, list):
		urls = [link.url for link in category_links if isinstance(link, Link)]
		category_sign = '/wiki/Category:'
		category_urls = [url for url in urls if category_sign in url]
		return [url[url.find(category_sign) + len(category_sign):] for url in category_urls]
	else:
		return []


def is_good_link(_link):
	unacceptable = [
		'/w/index.php?', '/wiki/Special:', '/wiki/Help:',
		'/wiki/Wikipedia:', 'https://foundation.wikimedia.org',
		'/wiki/Talk:', '/wiki/Portal:', '/shop.wikimedia.org',
		'www.mediawiki.org', '/wiki/Main_Page', 'wikimediafoundation.org',
		'/wiki/Template:', '/wiki/Template_talk:'
	]
	for x in unacceptable:
		if x in _link:
			return False
	return True


def find_links_in_tables(soup, base_url):
	result = {}
	for table in soup.find_all('table'):
		for item in table.find_all('li'):
			for link in item.find_all('a'):
				parsed_link = parse_link(element=link, base=base_url)
				if isinstance(parsed_link, Link):
					if parsed_link.url == 'http://SEEALSO':
						break
					result[id(link)] = parsed_link
			else:
				continue

			break

		else:
			continue

		break

	return result


def find_links_in_list(soup, base_url):
	result = {}
	for html_list in soup.find_all(['ol', 'ul']):
		for item in html_list.find_all('li'):
			children = item.children
			try:
				first_child = next(children)
			except:
				try:
					first_child = children[0]
				except:
					continue
			link = find(elements=first_child, name='a')
			if isinstance(first_child, (BeautifulSoup, Tag)):
				parsed_link = parse_link(element=link, base=base_url)
				if isinstance(parsed_link, Link):
					if parsed_link.url == 'http://SEEALSO':
						break
					result[id(link)] = parsed_link
		else:
			continue

		break

	return result


def get_anchors_and_links(soup, base_url):
	table_links = find_links_in_tables(soup=soup, base_url=base_url)
	links_in_lists = {
		i: link for i, link in find_links_in_list(soup=soup, base_url=base_url).items()
		if i not in table_links
	}
	return {
		'list_link_and_anchors': list(links_in_lists.values()),
		'table_links_and_anchors': list(table_links.values())
	}


def find_main_links_in_tables(tables):
	result = {}
	for table in tables:
		for col in table.columns:
			links = [x for x in table[col] if isinstance(x, Link)]
			link_lists = [
				maybe_link for lists in [x for x in table[col] if isinstance(x, list)]
				for maybe_link in lists if isinstance(maybe_link, Link)
			]
			links = links + link_lists
			if len(links) > 0:
				result[str(col)] = links

	return result


def get_main_paragraphs(body):
	_paragraphs_and_headers = body.find_all(['p', 'h1', 'h2', 'h3'])
	paragraphs = []
	for tag in _paragraphs_and_headers:
		if tag.name == 'p':
			paragraphs.append(tag)
		else:
			if tag.text == 'SEEALSO':
				break
	return paragraphs



