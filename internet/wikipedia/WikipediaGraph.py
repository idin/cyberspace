import re
from abstract import Graph
from slytherin.collections import flatten
from .Page_class import Page


class WikipediaGraph(Graph):
	def __init__(self, page, depth=1, strict=True, ordering=True):
		"""
		:type page: Page
		"""
		super().__init__(obj=None, strict=strict, ordering=ordering)

		self._go_deep(page=page, depth=depth)

	def _go_deep(self, page, depth):
		if page['id'] not in self:
			self.add_node(name=page['id'], label=page['title'])
		if depth>0:
			link_lists = page['link_lists']
			if link_lists:
				for link in flatten(link_lists):
					if re.match('^https://.+\.wikipedia.org/', link['url']):
						child = Page(api=page.api, url=link['url'])
						self._go_deep()


