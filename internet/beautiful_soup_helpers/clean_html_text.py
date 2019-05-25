from .clone_beautiful_soup_tag import clone_beautiful_soup_tag


def replace_images_with_text(element):
	html = clone_beautiful_soup_tag(element)
	for elem in html.find_all('img'):
		if 'alt' in elem.attrs:
			elem.string = elem.attrs['alt']
	return html

def clean_html_text(html, replace_images=False):
	if isinstance(html, str):
		return html
	else:
		if replace_images:
			html = replace_images_with_text(element=html)
		text = html.get_text()
		return ' '.join(text.replace('\n', ' ').replace('\xa0', ' ').strip().split())
