from setuptools import setup, find_packages


def readme():
	with open('./README.md') as f:
		return f.read()


setup(
	name='internet',
	version='2019.12.29.4',
	license='MIT',

	url='https://github.com/idin/internet',
	author='Idin',
	author_email='py@idin.ca',

	description='Python library for navigating the internet',
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
		'requests', 'bs4', 'selenium', 'chronometry',
		'slytherin', 'abstract', 'pensieve', 'linguistics', 'pandas', 'ravenclaw', 'silverware'
	],
	python_requires='~=3.6',
	zip_safe=False
)
