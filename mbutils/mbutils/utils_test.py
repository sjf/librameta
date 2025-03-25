#!/usr/bin/env python
import pytest
from mbutils.utils import *

url_params_input = [
    ('/', {}),
    ('https://foo.bar', {}),
    ('/?foo=bar&buz=bux', {'foo':['bar'], 'buz': ['bux']}),
    ('/?foo=bar&foo=buz', {'foo':['bar','buz']}),
    ('/?foo=bar%20buz', {'foo': ['bar buz']}),
    ('https://host:9999/search-adv?title=richter+10&author=Clarke%2C+Arthur+C%2C+McQuay%2C+Mike&series=&lang=eng&year=&end_year=&ext=epub',
      {'title': ['richter 10'], 'author': ['Clarke, Arthur C, McQuay, Mike'], 'end_year': [''],
      'ext': ['epub'], 'lang': ['eng'],'series': [''],'year': ['']})
]
@pytest.mark.parametrize('input, expected', url_params_input)
def test_url_params(input, expected):
  assert url_params(input) == expected


replace_url_param_input = [
    (('http://foo.com/?foo=bar', 'foo', 'buz'), 'http://foo.com/?foo=buz'),
    (('http://foo.com/?foo=bar', 'foo', 'bar buz'), 'http://foo.com/?foo=bar+buz'),
    (('http://foo.com/', 'foo', 'buz'), 'http://foo.com/?foo=buz'),
    (('http://foo.com/?foo=bar&foo=bob', 'foo', 'buz'), 'http://foo.com/?foo=buz')
]
@pytest.mark.parametrize('input, expected', replace_url_param_input)
def test_replace_url_param(input, expected):
  assert replace_url_param(*input) == expected
