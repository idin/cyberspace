from chronometry.date import get_today
import re


RESOLUTION_MARKERS0 = [
	'2160p', '1440p', '1080p', '720p', '480p', '360p', '240p',
	'4k', '8k'
]

RESOLUTION_MARKERS = RESOLUTION_MARKERS0 + [f'[{x}]' for x in RESOLUTION_MARKERS0]


def is_resolution(string):
	return string.lower() in RESOLUTION_MARKERS


def is_year(string, year_min, year_max):
	string = str(string)

	if re.search(r'^\(\d{4}\)$', string):
		return year_min <= int(string.strip('()')) <= year_max
	elif re.search(r'^\d{4}$', string):
		return year_min <= int(string) <= year_max
	else:
		return False


def get_title_year_and_resolution(name, sep=None, year_min=1950):
	year_max = get_today().year

	title_and_year_part = []
	resolution_part = []

	title_part = True

	name = name.replace('.', ' ')

	if sep is None:
		if len(name.split(' ')) > len(name.split('.')):
			sep = ' '
		else:
			sep = '.'

	for x in name.split(sep):
		if is_resolution(x):
			title_part = False

		if title_part:
			title_and_year_part.append(x)

		elif is_resolution(x):
			resolution_part.append(x.lower().strip('[]'))

	title_part_reversed = []
	year = None

	for x in reversed(title_and_year_part):
		if year is None:
			if is_year(string=x, year_min=year_min, year_max=year_max):
				year = int(x.strip('()'))

		else:
			title_part_reversed.append(x)

	title_part = reversed(title_part_reversed)

	return {
		'title': ' '.join(title_part),
		'year': year,
		'resolution': ' '.join(resolution_part)
	}











