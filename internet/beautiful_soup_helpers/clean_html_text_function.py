from .clone_beautiful_soup_tag import clone_beautiful_soup_tag


def clean_html_text(html, replace_images_with_text=False):
	if isinstance(html, str):
		text = html
	else:
		if replace_images_with_text:
			html = clone_beautiful_soup_tag(html)
			for elem in html.find_all('img'):
				if 'alt' in elem.attrs:
					elem.string = elem.attrs['alt']
		text = html.get_text()
	return ' '.join(text.replace('\n', ' ').replace('\xa0', ' ').strip().split())
