from imdb import IMDb
from imdb.Movie import Movie

_IMDb = IMDb()


class IMDB:
	def __init__(self, cache=None):
		self._imdb = _IMDb
		self._cache = cache
		if self._cache:
			self.search = self._cache.make_cached(
				id='imdb_search',
				function=self._search,
				condition_function=self._search_result_valid,
				sub_directory='search'
			)
		else:
			self.search = self._search

	def _search(self, title, year=None):
		"""
		:type title: str
		:type year: int
		:rtype: Movie
		"""
		movies = self._imdb.search_movie(title=title)

		if len(movies) == 0:
			print(f'{title} ({year}) not found!')
			return False

		if year is not None:
			for movie in movies:
				if movie.data['year'] == year:
					return self._imdb.get_movie(movie.movieID)

		return self._imdb.get_movie(movies[0].movieID)

	@staticmethod
	def _search_result_valid(result):
		if result is False:
			return False
		else:
			return True
