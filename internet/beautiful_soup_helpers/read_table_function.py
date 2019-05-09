import pandas as pd
import copy

from .clone_beautiful_soup_tag import clone_beautiful_soup_tag
from .clean_html_text_function import clean_html_text

def get_table_shape(table):
	num_columns = 0
	num_header_rows = 0
	num_rows = 0

	for row in table.find_all("tr"):
		col_tags = row.find_all(["td", "th"])
		if len(col_tags) > 0:
			if row.find('th'):
				num_header_rows += 1
			else:
				num_rows += 1
			if len(col_tags) > num_columns:
				num_columns = len(col_tags)
	return {'num_header_rows': num_header_rows, 'num_rows': num_rows, 'num_columns': num_columns}


def join_html_texts(texts):
	string = ' '.join([text for text in texts if isinstance(text, str)])
	return clean_html_text(string)


def read_table(table, text_only=False):
	table = clone_beautiful_soup_tag(table)
	for elem in table.find_all(["br"]):
		elem.replace_with(elem.text + "\n")

	table_shape = get_table_shape(table=table)

	# Create dataframe
	dataframe = pd.DataFrame(index=range(0, table_shape['num_rows']), columns=range(0, table_shape['num_columns']))
	header = pd.DataFrame(index=range(0, table_shape['num_header_rows']), columns=range(0, table_shape['num_columns']))

	# Create list to store rowspan values
	skip_index = [0 for i in range(0, table_shape['num_columns'])]

	# Start by iterating over each row in this table...
	row_counter = 0
	header_row_counter = 0

	for row in table.find_all("tr"):
		is_header = row.find('th') is not None

		# Skip row if it's blank
		if len(row.find_all(["td", "th"])) > 0:

			# Get all cells containing data in this row
			columns = row.find_all(["td", "th"])
			col_dim = []
			row_dim = []
			col_dim_counter = -1
			row_dim_counter = -1
			col_counter = -1
			this_skip_index = copy.deepcopy(skip_index)

			for col in columns:

				# Determine cell dimensions
				colspan = col.get("colspan")
				if colspan is None:
					col_dim.append(1)
				else:
					col_dim.append(int(colspan))
				col_dim_counter += 1

				rowspan = col.get("rowspan")
				if rowspan is None:
					row_dim.append(1)
				else:
					row_dim.append(int(rowspan))
				row_dim_counter += 1

				# Adjust column counter
				if col_counter == -1:
					col_counter = 0
				else:
					col_counter = col_counter + col_dim[col_dim_counter - 1]

				while skip_index[col_counter] > 0:
					col_counter += 1

				# Get cell contents
				if is_header:
					cell_data = clean_html_text(col, replace_images_with_text=True)
				elif text_only:
					cell_data = clean_html_text(col, replace_images_with_text=False)
				else:
					cell_data = col

				# Insert data into cell
				if is_header:
					if colspan is None:
						num_columns_in_cell = 1
					else:
						num_columns_in_cell = int(colspan)
					for i in range(num_columns_in_cell):
						header.iat[header_row_counter, col_counter + i] = cell_data
				else:
					dataframe.iat[row_counter, col_counter] = cell_data

				# Record column skipping index
				if row_dim[row_dim_counter] > 1:
					this_skip_index[col_counter] = row_dim[row_dim_counter]

		# Adjust row counter
		if is_header:
			header_row_counter += 1
		else:
			row_counter += 1

		# Adjust column skipping index
		skip_index = [i - 1 if i > 0 else i for i in this_skip_index]
	columns = [join_html_texts(header[col].values) for col in header.columns]
	dataframe.columns = columns
	return dataframe.reset_index(drop=True)
