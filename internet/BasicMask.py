from .find_common import find_common


class BasicMask:
	def __init__(self, prefix, suffix):
		"""
		:param str prefix: left side of the mask
		:param str suffix: right side of the mask
		"""
		self._prefix = str(prefix)
		self._suffix = str(suffix)

	def __getstate__(self):
		return self._prefix, self._suffix

	def __setstate__(self, state):
		self._prefix = state[0]
		self._suffix = state[1]

	def __eq__(self, other):
		"""
		:type other: BasicMask
		:rtype: bool
		"""
		return self._prefix == other._prefix and self._suffix == other._suffix

	def __ne__(self, other):
		return not self.__eq__(other)

	def __repr__(self):
		return f'"{self._prefix}", "{self._suffix}"'

	def __str__(self):
		return self.__repr__()

	def copy(self):
		return self.__class__(prefix=self._prefix, suffix=self._suffix)

	def is_in(self, string):
		"""
		:param str string: string to be check for existence of the mask
		:rtype: bool
		"""
		if self._prefix not in string:
			return False
		else:
			right_side = string.split(self._prefix, maxsplit=1)[1]
			return self._suffix in right_side

	def apply(self, string):
		"""
		:param str string:
		:rtype: list[str]
		"""
		if not self.is_in(string=string):
			return []

		else:
			split1 = string.split(sep=self._prefix)
			if string.startswith(self._prefix):
				to_the_right_of_prefix = split1
			else:
				to_the_right_of_prefix = split1[1:]

			sandwiched = [x for x in to_the_right_of_prefix if self._suffix in x]
			sandwiched = [x.split(self._suffix, maxsplit=1)[0] for x in sandwiched]
			return sandwiched

	def intersect(self, others):
		"""
		:param BasicMask or list[BasicMask] others: another mask or other masks
		:rtype: BasicMask
		"""
		if isinstance(others, self.__class__):
			others = [others]
		prefixes = [self._prefix] + [x._prefix for x in others]
		suffixes = [self._suffix] + [x._suffix for x in others]
		return self.__class__(
			prefix=find_common(strings=prefixes, side='right'),
			suffix=find_common(strings=suffixes, side='left')
		)

	def __mul__(self, other):
		return self.intersect(others=other)
