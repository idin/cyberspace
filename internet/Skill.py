from .find_common import find_common


class Template:
	def __init__(self):
		self._left = None
		self._right = None

	def train(self, targets, string):
		splits = [string.split(t) for t in targets]
		before_afters = {t:(s[:-1], s[1:]) for t in targets for s in string.split(t)}
		num_before_afters = len(splits[0])-1
		common_before_afters = [
			(
				find_common([ba[i][0] for ba in before_afters.values()], side='left'),
				find_common([ba[i][1] for ba in before_afters.values()], side='right')
			)
			for i in range(num_before_afters)
		]



