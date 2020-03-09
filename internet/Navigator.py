"""
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome, Firefox
"""
import requests
from requests.adapters import SSLError
from bs4 import BeautifulSoup

import time
import warnings
from chronometry import MeasurementSet


class Navigator:
	def __init__(self, driver=None, user_agent=None, request_method='urllib', timeout=10):
		"""
		:type driver: str or ChromeDriver or FirefoxDriver or NoneType
		:param str user_agent: the default user agent, one of random, ie, ff, chrome, etc.
		"""

		'''
		if isinstance(driver, str):
			if driver.lower() == 'chrome':
				driver = Chrome()
			elif driver.lower() == 'firefox':
				driver = Firefox()
			else:
				raise ValueError(f'Unknown driver: "{driver}"')
		else:
			if driver is None and request_method != 'urllib':
				raise ValueError(f'Driverless Navigator only works with urllib method, not with "{request_method}"!')
		'''
		self._driver = driver

		try:
			self._user_agent = user_agent.random
		except:
			self._user_agent = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Mobile Safari/537.36'

		self._default_request_method = request_method
		self._timeout = timeout
		self._url = None
		self._page_source = None
		self._parsed_html = None
		self._measurement_set = MeasurementSet()

		#self.get = self._measurement_set.measure(function=self._get, name='get')
		#self.parse_html = self._measurement_set.measure(function=self._parse_html, name='parse_html')
		self.get = self._get
		self.parse_html = self._parse_html

	def __del__(self):
		self.driver.quit()

	@property
	def driver(self):
		"""
		:rtype: ChromeDriver or FirefoxDriver
		"""
		return self._driver

	def _get_by_driver(self, url, element_id=None, timeout_exception='error'):
		self.driver.get(url=url)
		if element_id is None:
			time.sleep(self._timeout)
		else:
			try:
				element_present = expected_conditions.presence_of_all_elements_located((By.ID, element_id))
				WebDriverWait(driver=self.driver, timeout=self._timeout).until(element_present)

			except TimeoutException:
				self._page_source = None
				if timeout_exception[0].lower == 'e':
					raise TimeoutException(f'Timed out waiting for page:"{url}" to load!')
				elif timeout_exception[0].lower == 'w':
					warnings.warn(message=f'Timed out waiting for page:"{url}" to load!')
		return self.driver.page_source

	def _get_by_urllib(self, url, headers=None, json=False):
		headers = headers or {
			'user-agent': self._user_agent
		}
		request = requests.get(url=url, headers={'User-Agent': self._user_agent})
		'''
		request = urllib.request.Request(url)
		
		#for key, value in headers.items():
			request.add_header(key=key, val=value)

		if json:
			response = urllib.request.urlopen(request, timeout=self._timeout)
			return load_json(response)
		else:
			with urllib.request.urlopen(request, timeout=self._timeout) as response:
				html = response #.read().decode(encoding)
			return html
		'''
		if format == 'json':
			try:
				r = requests.get(url, params=parameters, headers=headers)
				result = r.json()
			except SSLError as e:
				warnings.warn(str(e))
				result = None

	def _get(
			self, url, request_method=None, element_id=None, get_json_back=False,
			timeout_exception='error', parser='lxml'
	):
		"""
		:type url: str
		:param str or NoneType request_method: one of 'urllib' or 'selenium' or None, None will choose the default
		:param str or NoneType user_agent: one of None (to choose default), random, ie, ff, etc.
		:type element_id: str or NoneType
		:type encoding: str
		:rtype: BeautifulSoup or str
		"""
		self._url = url
		request_method = request_method or self._default_request_method

		if request_method.lower() == 'urllib':
			html = self._get_by_urllib(url=url, json=get_json_back)

		elif request_method.lower() == 'selenium':
			html = self._get_by_driver(url=url, element_id=element_id, timeout_exception=timeout_exception)

		else:
			raise ValueError(f'Unknown method: "{method}"!')

		self._page_source = html

		if parser:
			return self.parse_html(parser=parser, html=html)

		else:
			return self._page_source

	def _parse_html(self, html, parser='lxml'):
		"""
		:type parser: str
		:type html: str
		:rtype: BeautifulSoup
		"""
		self._parsed_html = BeautifulSoup(html, parser)
		return self._parsed_html

	@property
	def loading_time(self):
		return self._get_timer.get_mean_elapsed(unit='sec')

	@property
	def parsing_time(self):
		return self._parse_timer.get_mean_elapsed(unit='sec')
