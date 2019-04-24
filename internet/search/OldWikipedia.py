from .Query import Query
import wikipedia
from wikipedia import DisambiguationError
import warnings

class Wikipedia:
	@staticmethod
	def search(query, num_results=10, suggestion=False):
		q = Query(query=query)
		q['search_result'] = wikipedia.search(query=q['query'], results=num_results, suggestion=suggestion)

	@classmethod
	def get_page(cls, title, ignore_disambiguation_error=True, num_results=1):
		q = Query(page_title=title)
		if not ignore_disambiguation_error:
			# vanilla call
			with warnings.catch_warnings():
				warnings.simplefilter('ignore')
				result = wikipedia.page(title=title)
			return result

		else:
			# call with exception capture
			try:
				with warnings.catch_warnings():
					warnings.simplefilter('ignore')
					result = wikipedia.page(title=title)

			except DisambiguationError as disambiguation:
				if num_results is None:
					num_results = len(disambiguation.options)
				else:
					num_results = min(num_results, len(disambiguation.options))

				if num_results == 1:
					result = cls.get_page(
						title=disambiguation.options[0], ignore_disambiguation_error=ignore_disambiguation_error, num_results=num_results
					)
				else:
					result = {
						x: cls.get_page(
							title=x, ignore_disambiguation_error=ignore_disambiguation_error, num_results=num_results
						)
						for x in disambiguation.options[:num_results]
					}

			return result
