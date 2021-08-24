from .BasicMask import BasicMask


class Mask(BasicMask):
	def __add__(self, other):
		return self.combine(others=other)

	def combine(self, others):
		"""
		:param BasicMask or list[BasicMask] others: another mask or other masks
		:rtype: MaskSet
		"""
		if isinstance(others, self.__class__):
			others = [others]
		return MaskSet(masks=[self] + others)


class MaskSet:

	def __init__(self, masks=None):
		"""
		:param list[tuple] or list[BasicMask] masks: prefixes and suffixes in tuples
		"""

		self._masks = []

		masks = masks or []
		for x in masks:
			self.append(x=x)

	def __getstate__(self):
		return self._masks

	def __setstate__(self, state):
		self._masks = state

	def __repr__(self):
		return '\n'.join([str(x) for x in self._masks])

	def __str__(self):
		return self.__repr__()

	def train(self, string, target, inplace=True):
		print('training')
		"""
		:param str string: a string that might contain a target
		:param str target: the substring that might be contained in the string
		:param bool inplace: if True this maskset will be trained, otherwise a new maskset will be returned
		:rtype: MaskSet or NoneType
		"""
		if target not in string:
			raise ValueError('the string does not contain the target!')

		mask_set = self.__class__()
		splits = str(string).split(str(target))
		for i in range(len(splits)-1):
			mask_set.append((splits[i], splits[i+1]))
		print('mask_set:', mask_set, '\n')
		if inplace:
			if len(self._masks) == 0:
				self._masks = mask_set._masks
			else:
				self.intersect(others=mask_set, inplace=True)
		else:
			if len(self._masks) == 0:
				return mask_set
			else:
				return self.intersect(others=mask_set, inplace=False)

	def copy(self):
		return self.__class__(masks=self._masks)

	def append(self, x):
		if isinstance(x, BasicMask):
			mask = x.copy()
		else:
			mask = BasicMask(prefix=x[0], suffix=x[1])
		if mask not in self._masks and mask._prefix != '' and mask._suffix != '':
			self._masks.append(mask)

	def intersect(self, others, inplace=False):
		"""
		:type others: MaskSet or list[MaskSet]
		:param bool inplace: if True, this object will be affected, otherwide a new one is returned
		:rtype: MaskSet
		"""

		if isinstance(others, MaskSet):
			others = [others]

		result = self if inplace else self.copy()

		for other in others:
			intersection = self.__class__(masks=[])
			for mask in result._masks:
				for other_mask in other._masks:
					intersection.append(mask * other_mask)
			result._masks = intersection._masks

		if not inplace:
			return result

	def __mul__(self, other):
		"""
		:param list[MaskSet] or MaskSet other: other mask
		:rtype: MaskSet
		"""
		return self.intersect(others=other, inplace=False)
