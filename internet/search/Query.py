from datetime import datetime
from chronology import get_elapsed_seconds
from pensieve import Pensieve


class Query:
	def __init__(self, **kwargs):
		self._pensieve = Pensieve()
		self._timestamps = dict()
		self._durations = dict()
		for key, value in kwargs.items():
			self.store(key=key, content=value)

	@property
	def pensieve(self):
		"""
		:rtype: Pensieve
		"""
		return self._pensieve

	def __getstate__(self):
		return {
			'pensieve': self._pensieve,
			'timestamps': self._timestamps,
			'durations': self._durations
		}

	def __setstate__(self, state):
		self._pensieve = state['pensieve']
		self._timestamps = state['timestamps']
		self._durations = state['durations']
		self._last_timestamp = datetime.now()

	def store(self, key, content=None, precursors=None, function=None, materialize=True):
		start_time = datetime.now()
		self.pensieve.store(
			key=key, content=content, precursors=precursors, function=function,
			materialize=materialize
		)
		self._timestamps[key] = datetime.now()
		self._durations[key] = get_elapsed_seconds(start=start_time, end=self._timestamps[key])

	def __getitem__(self, item):
		return self.pensieve[item]

	def get_timestamp(self, item):
		return self._timestamps[item]

	def get_duration(self, item):
		return self._durations[item]
