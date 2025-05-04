from setuptools import setup, find_packages

setup(
    name='mbutils',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
      'humanfriendly',
      'sendgrid',
      'unidecode',
    ],
)
