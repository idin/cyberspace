from setuptools import setup, find_packages


def readme():
	with open('./README.md') as f:
		return f.read()


setup(
	name='cyberspace',
	version='2022.1.25',
	license='MIT',

	url='https://github.com/idin/cyberspace',
	author='Idin',
	author_email='py@idin.ca',

	description='Python library for navigating the world wide web',
	long_description=readme(),
	long_description_content_type='text/markdown',

	classifiers=[
		'Development Status :: 3 - Alpha',
		'Intended Audience :: Developers',
		'Programming Language :: Python :: 3 :: Only',
		'Programming Language :: Python :: 3.6',
		'Programming Language :: Python :: 3.7',
		'Topic :: Software Development :: Libraries :: Python Modules'
	],

	packages=find_packages(exclude=["jupyter_tests", ".idea", ".git"]),
	install_requires=[
		'IMDbPy', 'bs4', 'requests_ntlm',
		'pandas', 'requests',
		'chronometry', 'slytherin', 'abstract', 'pensieve', 'ravenclaw', 'silverware'
	],
	python_requires='~=3.6',
	zip_safe=False
)
