from pensieve import Pensieve


class Query:
	def __init__(self, **kwargs):
		self._pensieve = Pensieve()
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
			'pensieve': self._pensieve
		}

	def __setstate__(self, state):
		self._pensieve = state['pensieve']

	def store(self, key, content=None, precursors=None, function=None, materialize=True):
		self.pensieve.store(
			key=key, content=content, precursors=precursors, function=function,
			materialize=materialize
		)

	def __getitem__(self, item):
		return self.pensieve[item]

