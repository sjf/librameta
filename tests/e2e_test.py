import pytest
import requests
import http.client
import os
import re
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
from mbutils import *

config = load_config({'BACKEND': 'https://localhost', 'IS_FLASK': False, 'IS_GUNICORN': False})

BACKEND = re.sub('/$','', config['BACKEND']) # remove tailing slash from backend.
TIMEOUT = config['PYTEST_TIMEOUT']
VERIFY_SSL = config['VERIFY_SSL']
HEADERS = {'User-Agent': f"python-requests/lmlmlm/{requests.__version__}"}

@pytest.fixture
def client():
  pass

def get(path, params={}, auth=None):
  url = BACKEND + path
  response = requests.get(url, params, timeout=TIMEOUT, verify=VERIFY_SSL, auth=auth, headers=HEADERS, allow_redirects=False)
  print(f"\nGET {response.url}")
  return response

def post(path, body):
  url = BACKEND + path
  response = requests.post(url, data=body, timeout=TIMEOUT, verify=VERIFY_SSL, allow_redirects=False, headers=HEADERS)
  print(f"\nPOST {response.url}")
  if response.status_code == 301:
    redirect_url = response.headers.get('Location')
    # Strictly you should only do a GET on a redirect URL.
    response = requests.post(redirect_url, data=body, timeout=TIMEOUT, verify=VERIFY_SSL, allow_redirects=False, headers=HEADERS)
    print(f"\nPOST {response.url}")
  return response

def assert_code(response, expected_code):
  code = response.status_code
  print(f"RESP {code} {http.client.responses[code]}")
  assert response.status_code == expected_code, f"Wanted HTTP response code {expected_code}, Got {code} {http.client.responses[code]}\n{dictl(response.headers)}\n\n{response.text}"

def assert_contains(response, text):
  assert_code(response, 200)
  assert text in response.text, f"Wanted '{text}'. Got:\n{dictl(response.headers)}\n\n{response.text}"

def assert_results_same(expected_response, response):
  assert response.status_code == expected_response.status_code

  expected_results = get_results(expected_response)
  results = get_results(response)
  assert results == expected_results

def get_results(response):
  soup = BeautifulSoup(response.text, 'html.parser')
  return soup.find_all('div', class_='book')

####### CUJs

def test_index(client):
  response = get('/')
  assert_contains(response, 'Search by title')
  assert 'X-LMLMLM' in response.headers

def test_index_http_redirect(client):
  if config['IS_FLASK'] or config['IS_GUNICORN'] or BACKEND.startswith('http://'):
    # Flask and gunicorn don't listen on both ports.
    # Testing only with http means https is not available.
    pytest.skip(f"Skipping http->https redirect test for backend:{BACKEND}")
  https_url = BACKEND + '/test?foo=bar'
  http_url = https_url.replace('https://', 'http://', 1)
  response = requests.get(http_url, timeout=TIMEOUT, allow_redirects=False, headers=HEADERS)
  redirect_url = response.headers.get('Location')

  assert_code(response, 301)
  assert redirect_url == https_url

def test_index_invalid_param_ignored(client):
  response = get('/', params={'foo': 'bar'})
  response2 = get('/')
  assert_contains(response, 'Search by title')
  assert response.text == response2.text

def test_result_fields_populated(client):
  response = get('/search', params={'search': 'Hans-Joachim Böckenhauer (Author), Dirk Bongartz (Author)'})
  assert_code(response, 200)
  soup = BeautifulSoup(response.text, 'html.parser')

  assert soup.select_one('.book img.cover-image')['src'] == 'https://covers.openlibrary.org/b/isbn/3540719121-M.jpg'
  assert soup.select_one('.book div.title').text == 'Algorithmic Aspects of Bioinformatics'
  assert soup.select_one('.book div.edition').text == '1st Edition'
  assert soup.select_one('.book div.series').text == 'Natural Computing Series'
  assert soup.select_one('.book a.series-link')['href'] == '/?series=Natural%20Computing%20Series'
  assert soup.select_one('.book span.year').text.strip() == '2007'
  assert soup.select_one('.book span.lang').text == 'English'
  assert soup.select_one('.book div.pages').text == '406 pages'
  assert soup.select_one('.book span.file-extension').text == 'pdf'
  assert soup.select_one('.book span.size').text == '3 Mb'
  # First download link
  assert soup.select_one('.book a.download')['href'] == config['DIRECT_DL_URL_BASE']+'main/549000/342645e3721601a3f6c1b3c1dd9294f0/%28Natural%20Computing%20Series%29%20Hans-Joachim%20B%C3%B6ckenhauer%20%28Author%29%2C%20Dirk%20Bongartz%20%28Author%29%20-%20Algorithmic%20Aspects%20of%20Bioinformatics%20%282007%29.pdf'
  assert soup.select_one('.book a.download')['data-position'] == '0'
  assert soup.select_one('.book a.download')['data-id'] == '342645E3721601A3F6C1B3C1DD9294F0'
  mirrors = soup.select('.dl-links .mirror-link')
  assert len(mirrors) >= 2
  # cdn_urls = split(config['CDN_URLS'])
  # assert mirrors[0]['href'] == cdn_urls[0].format(md5='342645E3721601A3F6C1B3C1DD9294F0', index='main')
  # assert mirrors[0]['data-position'] == '0'
  # assert mirrors[0]['data-id'] == '342645E3721601A3F6C1B3C1DD9294F0'
  # assert mirrors[1]['href'] == cdn_urls[1].format(md5='342645E3721601A3F6C1B3C1DD9294F0', index='main')
  # assert mirrors[1]['data-position'] == '0'
  # assert mirrors[1]['data-id'] == '342645E3721601A3F6C1B3C1DD9294F0'

  authors = soup.select_one('.book div.authors').text.strip()
  authors = re.sub('\\s+', ' ', authors)
  assert authors == 'Hans-Joachim Böckenhauer (Author), Dirk Bongartz (Author)'
  author_links = soup.select('a.author-link')
  assert len(author_links) == 2
  assert author_links[0].text == 'Hans-Joachim Böckenhauer'
  assert author_links[1].text == 'Dirk Bongartz'
  assert author_links[0]['href'] == '/?author=Hans-Joachim%20B%C3%B6ckenhauer'
  assert author_links[1]['href'] == '/?author=Dirk%20Bongartz'

def test_search_nonfiction_title_and_author(client):
  response = get('/search', params={'search': 'climbing bible Mobråten'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_nonfiction_title(client):
  response = get('/search', params={'search': 'climbing bible'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_nonfiction_author(client):
  response = get('/search', params={'search': 'Mobråten'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_fiction_title_and_author(client):
  response = get('/search', params={'search': 'richter 10 arthur c clarke'})
  assert_contains(response,'Richter 10')

def test_search_fiction_title(client):
  response = get('/search', params={'search': 'richter 10'})
  assert_contains(response,'Richter 10')

def test_search_fiction_author(client):
  response = get('/search', params={'search': 'Clarke, Arthur C McQuay, Mike'})
  assert_contains(response,'Richter 10')

def test_search_isbn(client):
  response = get('/search', params={'search': '183-98 11-0 48'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_doi(client):
  response = get('/search', params={'search': '10.1007/b102786'})
  assert_contains(response,'Tutorials in Mathematical Biosciences I: Mathematical Neuroscience')

def test_search_no_results(client):
  response = get('/search', params={'search': 'thistitledoesnotexist'})
  assert_contains(response,'No results')

def test_search_redirects(client):
  response = get('/', params={'search': 'climbing bible'})
  response2 = get('/search', params={'search': 'climbing bible'})
  redirect_url = response.headers.get('Location')

  assert_code(response, 301)
  assert redirect_url == url_wo_host(response2.url)

def test_adv_search_redirects(client):
  response = get('/', params={'title': 'climbing bible'})
  response2 = get('/search', params={'title': 'climbing bible'})
  redirect_url = response.headers.get('Location')

  assert_code(response, 301)
  assert redirect_url == url_wo_host(response2.url)

def test_search_spelling_correction(client):
  response = get('/search', params={'search': 'coing bostal'})
  assert_contains(response, 'Going Postal')

def test_search_no_spelling_correction_for_quotes(client):
  response = get('/search', params={'search': '"coing bostal"'})
  assert_contains(response, 'No results')

def test_search_unquoted_query_expands(client):
  response = get('/search', params={'search': 'climbing bible doesnotexist'})
  assert_contains(response, 'Found no exact matches')
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_partially_unquoted_query_expands(client):
  response = get('/search', params={'search': '"climbing bible" doesnotexist'})
  assert_contains(response, 'Found no exact matches')
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_quoted_query_does_not_expand(client):
  response = get('/search', params={'search': '"climbing bible doesnotexist"'})
  assert_contains(response, 'No results')

######### Search params

def test_search_by_title(client):
  response = get('/search', params={'title': 'climbing bible'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_by_author(client):
  response = get('/search', params={'author': 'Mobråten'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_by_series(client):
  response = get('/search', params={'series': 'Lecture Notes in Mathematics 1860'})
  assert_contains(response,'Tutorials in Mathematical Biosciences I: Mathematical Neuroscience')

def test_search_by_isbn(client):
  response = get('/search', params={'isbn': '1839811048'})
  assert_contains(response,'Climbing Bible')

def test_search_by_doi(client):
  response = get('/search', params={'doi': '10.1007/b102786'})
  assert_contains(response,'Tutorials in Mathematical Biosciences I: Mathematical Neuroscience')

######### Search filters

def test_filter_exts_neg(client):
  response = get('/search', params={'title': 'climbing bible', 'ext' : ['pdf','mobi','djvu']})
  assert_contains(response,'No results')

def test_filter_exts_pos(client):
  response = get('/search', params={'title': 'climbing bible',  'ext' : ['pdf','mobi','djvu','epub']})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_filter_exts_multiple(client):
  response = get('/search', params={'title': 'X-Treme Latin: All the Latin You Need to Know for Survival in the 21st Century'})
  results1 = get_results(response)
  # This is including PDF results.
  assert len(results1) >= 4
  response = get('/search', params={'ext' : ['mobi','epub'], 'title': 'X-Treme Latin: All the Latin You Need to Know for Survival in the 21st Century'})
  results2 = get_results(response)

  assert len(results2) < len(results1)
  for result in results2:
    ext = result.find('span', class_='file-extension').text
    assert ext in ['mobi','epub']

def test_filter_exts_invalid_ignored(client):
  response = get('/search', params={'title': 'climbing bible', 'ext' : ['epub','unknown']})
  assert_contains(response,'Unsupported file type')

  response2 = get('/search', params={'title': 'climbing bible', 'ext' : 'epub'})
  assert_results_same(response2, response)

def test_filter_lang_neg(client):
  response = get('/search', params={'title': 'climbing bible', 'lang' : 'rus'})
  assert_contains(response,'No results')

def test_filter_lang_pos(client):
  response = get('/search', params={'title': 'climbing bible', 'lang' : 'eng'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_filter_ext_and_langs_neg(client):
  response = get('/search', params={'title': 'climbing bible', 'lang' : 'rus', 'ext' : 'pdf' })
  assert_contains(response,'No results')

def test_filter_ext_and_langs_pos(client):
  response = get('/search', params={'title': 'climbing bible', 'lang' : 'eng', 'ext' : 'epub'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_filter_invalid_lang_ignored(client):
  response = get('/search', params={'title': 'climbing bible', 'lang' : 'unknown'})
  assert_contains(response, 'Invalid language')

  response2 = get('/search', params={'title': 'climbing bible'})
  assert_results_same(response2, response)

def test_year_filter_neg(client):
  response = get('/search', params={'title': 'climbing bible', 'year' : '2021'})
  assert_contains(response,'No results')

def test_year_filter_pos(client):
  response = get('/search', params={'title': 'climbing bible', 'year' : '2022'})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_year_filter_year_invalid_ignored(client):
  expected_response = get('/search', params={'title': 'climbing bible'})
  response = get('/search', params={'title': 'climbing bible', 'year' : 'foobar'})
  assert_contains(response, 'Year must be a number')
  assert_results_same(expected_response, response)

def test_year_filter_start_year(client):
  response = get('/search', params={'author': 'pratchett', 'start_year' : '2013'})
  soup = BeautifulSoup(response.text, 'html.parser')
  years = map(lambda x:int(x.text.strip()), soup.select('.book span.year'))
  assert years
  assert all(x >= 2013 for x in years), list(years)

def test_year_filter_start_year_invalid_ignored(client):
  expected_response = get('/search', params={'title': 'climbing bible'})
  response = get('/search', params={'title': 'climbing bible', 'start_year' : 'foobar'})
  assert_contains(response, 'Year must be a number')
  assert_results_same(expected_response, response)

def test_year_filter_end_end(client):
  response = get('/search', params={'author': 'pratchett', 'end_year' : '1988'})
  soup = BeautifulSoup(response.text, 'html.parser')
  years = map(lambda x:int(x.text.strip()), soup.select('.book span.year'))
  assert years
  assert all(x <= 1988 for x in years), list(years)

def test_year_filter_end_year_invalid_ignored(client):
  expected_response = get('/search', params={'title': 'climbing bible'})
  response = get('/search', params={'title': 'climbing bible', 'end_year' : 'foobar'})
  assert_contains(response, 'Year must be a number')
  assert_results_same(expected_response, response)

def test_year_filter_year_range(client):
  response = get('/search', params={'author': 'pratchett', 'start_year' : '2010', 'end_year' : '2013'})
  soup = BeautifulSoup(response.text, 'html.parser')
  years = map(lambda x:int(x.text.strip()), soup.select('.book span.year'))
  assert years
  assert all(2010 <= x <= 2013 for x in years), list(years)

####### Search query matches correctly.

def test_author_tokenizer_search_param(client):
  response = get('/search', params={'search': 'c.y. foo'})
  assert_contains(response,'Dominic C.Y. Foo')
  assert_contains(response,'Dominic C Y Foo')
  assert_contains(response,'Dominic C. Y. Foo')

def test_author_tokenizer_author_param(client):
  response = get('/search', params={'author': 'c.y. foo'})
  assert_contains(response,'Dominic C.Y. Foo')
  assert_contains(response,'Dominic C Y Foo')
  assert_contains(response,'Dominic C. Y. Foo')

def test_author_analyser_author_param_removes_title(client):
  response = get('/search', params={'author': 'c.y. foo (author)'})
  assert_contains(response,'Dominic C.Y. Foo')
  assert_contains(response,'Dominic C Y Foo')
  assert_contains(response,'Dominic C. Y. Foo')
  response = get('/search', params={'author': 'c.y. foo (eds.)'})
  assert_contains(response,'Dominic C.Y. Foo')
  assert_contains(response,'Dominic C Y Foo')
  assert_contains(response,'Dominic C. Y. Foo')
  response = get('/search', params={'author': 'c.y. foo (ред.)'})
  assert_contains(response,'Dominic C.Y. Foo')
  assert_contains(response,'Dominic C Y Foo')
  assert_contains(response,'Dominic C. Y. Foo')

def test_author_term_order_not_significant(client):
  response = get('/search', params={'author': 'Yusup, Suzana (author)'})
  assert_contains(response,'Suzana Yusup')

def test_search_ignores_puncutation(client):
  # All punctation is replaced with space, so it breaks tokens, except for apostrophe
  response = get('/search', params={'search': "c'limbing!\"#$%&\\'()*+,-./:;<=>?@[\\]^_`{|}~bible"})
  assert_contains(response,'The Climbing Bible: Practical Exercises')

def test_search_ignores_quotes(client):
  response = get('/search', params={'search': 'the hearts invisible furies'})
  response2 = get('/search', params={'search': 'the heart\'s invisible furies'})
  assert_contains(response,'The Heart&#39;s Invisible Furies')
  assert_contains(response2,'The Heart&#39;s Invisible Furies')
  assert_results_same(response, response2)

####### Order results

def test_sort_relevance_is_default_and_ignores_order_param(client):
  response = get('/search', params={'author': 'c.y. foo'})
  response2 = get('/search', params={'author': 'c.y. foo', 'sort' : 'relevance', 'order': 'desc'})
  response3 = get('/search', params={'author': 'c.y. foo', 'sort' : 'relevance', 'order': 'asc'})

  assert_results_same(response, response2)
  assert_results_same(response2, response3)

def test_sort_invalid_is_ignored(client):
  response = get('/search', params={'author': 'c.y. foo'})
  response2 = get('/search', params={'author': 'c.y. foo', 'sort' : 'foobar'})

  assert_contains(response2, 'Invalid sort parameter')
  assert_results_same(response, response2)

def test_order_invalid_is_ignored(client):
  response = get('/search', params={'author': 'c.y. foo'})
  response2 = get('/search', params={'author': 'c.y. foo', 'sort' : 'year', 'order': 'foobar'})

  assert_contains(response2, 'Invalid sort parameter')
  assert_results_same(response, response2)

def test_sort_year_desc_or_unspecified(client):
  response = get('/search', params={'author': 'c.y. foo', 'sort' : 'year'})
  response2 = get('/search', params={'author': 'c.y. foo', 'sort' : 'year', 'order': 'desc'})
  soup = BeautifulSoup(response.text, 'html.parser')
  years = mapl(lambda x:int(x.text.strip()), soup.select('.book span.year'))

  assert years
  assert years == sorted(years, reverse=True), years
  assert_results_same(response, response2)

def test_sort_year_order_asc(client):
  response = get('/search', params={'author': 'c.y. foo', 'sort' : 'year', 'order': 'asc'})
  soup = BeautifulSoup(response.text, 'html.parser')
  years = mapl(lambda x:int(x.text.strip()), soup.select('.book span.year'))

  assert years
  assert years == sorted(years), years

def test_sort_size_unspecified_or_desc(client):
  response = get('/search', params={'author': 'c.y. foo', 'sort' : 'size'})
  response2 = get('/search', params={'author': 'c.y. foo', 'sort' : 'size', 'order': 'desc'})
  soup = BeautifulSoup(response.text, 'html.parser')
  sizes = mapl(lambda x:int(x['data-bytes']), soup.select('.size'))

  assert sizes
  assert sizes == sorted(sizes, reverse=True), sizes
  assert_results_same(response, response2)

def test_sort_size_order_asc(client):
  response = get('/search', params={'author': 'c.y. foo', 'sort' : 'size', 'order': 'asc'})
  soup = BeautifulSoup(response.text, 'html.parser')
  sizes = mapl(lambda x:int(x['data-bytes']), soup.select('.size'))

  assert sizes
  assert sizes == sorted(sizes), sizes

####### Pagination

def test_pagination_start(client):
  response = get('/search', params={'search': 'pratchett'})
  soup = BeautifulSoup(response.text, 'html.parser')

  assert soup.find('a', id='next')['href']
  print(soup.find('a', id='prev'))
  assert not soup.find('a', id='prev')['href']

def test_pagination_middle(client):
  response = get('/search', params={'search': 'pratchett', 'page': '1'})
  soup = BeautifulSoup(response.text, 'html.parser')

  assert soup.find('a', id='next')['href']
  assert soup.find('a', id='prev')['href']

def test_pagination_end(client):
  response = get('/search', params={'search': 'pratchett', 'page': config['MAX_PAGE_NUM']})
  soup = BeautifulSoup(response.text, 'html.parser')

  # In the test dataset there are not a max number of results for any search
  # so the next button can be completely missing.
  assert not soup.find('a', id='next') or not soup.find('a', id='next')['href']
  # assert soup.find('a', id='prev')['href']

def test_pagination_invalid_num_ignored(client):
  response = get('/search', params={'search': 'pratchett', 'page': 'foobar'})
  expected_response = get('/search', params={'search': 'pratchett'})
  assert_results_same(expected_response, response)

def test_pagination_num_too_big_flashes(client):
  response = get('/search', params={'search': 'pratchett', 'page': config['MAX_PAGE_NUM'] + 1})
  assert_contains(response, 'Something went wrong')
  expected_response = get('/search', params={'search': 'pratchett'})
  assert_results_same(expected_response, response)

####### Post-search processing

def test_rm_duplicate_authors(client):
  response = get('/search', params={'search': 'Recent advances in sustainable process design and optimization'})
  soup = BeautifulSoup(response.text, 'html.parser')
  div = soup.find('div', class_='authors')
  assert(re.sub('\\s+', ' ', div.text.strip()) == "Dominic C Y Foo, Mahmoud M El-Halwagi, Raymond R Tan")

####### Other pages

def test_health(client):
  response = get('/health')
  assert_contains(response, 'OK')

def test_feedback(client):
  response = get('/feedback')
  assert_contains(response, 'contact@librameta.net')

def test_thankyou(client):
  response = post('/thankyou',{'email':'lmlmlm@example.com','message':'lmlmlm-message'})
  assert_contains(response, 'Thank you')

def test_about(client):
  response = get('/about')
  assert_contains(response, 'privacy')

def test_log(client):
  response = post('/log', '{"name": "download", "data": {"urlpath": "/search?title=bitter+secrets", "position": "0", "id": "33CE48DC3FDDC2584557725D71278064", "title": "Bitter Secrets", "authors": "Mia Knight"}}')
  assert_code(response, 200)

####### Protected pages

def test_mb_is_protected(client):
  if config['IS_FLASK'] or config['IS_GUNICORN']:
    pytest.skip("Skipping test on flask and gunicorn.")
  response = get('/mb/index.html')
  assert_code(response, 401)

def test_mb_with_auth(client):
  if config['IS_FLASK'] or config['IS_GUNICORN']:
    pytest.skip("Skipping test on flask and gunicorn.")
  response = get('/mb/index.html', auth=HTTPBasicAuth(config['HT_USERNAME'], read_value(config['HT_PASSWORD_FILE'])))
  assert_contains(response, 'Admin')

def test_files_is_protected(client):
  if config['IS_FLASK'] or config['IS_GUNICORN']:
    pytest.skip("Skipping test on flask")
  response = get('/files/test.txt')
  assert_code(response, 401)

def test_files_with_auth(client):
  if config['IS_FLASK'] or config['IS_GUNICORN']:
    pytest.skip("Skipping test on flask and gunicorn.")
  response = get('/files/test.txt', auth=HTTPBasicAuth(config['FILES_HT_USERNAME'], read_value(config['FILES_HT_PASSWORD_FILE'])))
  assert_code(response, 200)

### CDN is working

def test_can_download_main_direct(client):
  if not config['TEST_DOWNLOAD']:
    pytest.skip("Skipping download tests")
  response = get('/search', params={'search': 'climbing bible'})
  soup = BeautifulSoup(response.text, 'html.parser')
  link = soup.find('a', class_='download')['href']

  print(link)
  response = requests.head(link)

  assert 'Content-Disposition' in response.headers
  value = response.headers['Content-Disposition']
  assert value.startswith('attachment; filename="')
  assert "Exercises _ Technique and strength training for climbing-Vertebrate Publishing (2022).epub" in value

def test_can_download_main_mirrors(client):
  if not config['TEST_DOWNLOAD']:
    pytest.skip("Skipping download tests")
  response = get('/search', params={'title': 'climbing bible'})
  soup = BeautifulSoup(response.text, 'html.parser')
  mirrors = soup.select('.mirrors a')
  assert len(mirrors) == 2

  for mirror in mirrors:
    link = mirror['href']
    print(link)
    response = requests.get(link)

    assert_contains(response, 'The Climbing Bible: Practical Exercises')
    soup = BeautifulSoup(response.text, 'html.parser')
    a = soup.find('a', string='GET')
    assert a
    link = a['href']
    assert link.startswith("get.php?md5=") or "Climbing" in link

def test_can_download_fiction_direct(client):
  if not config['TEST_DOWNLOAD']:
    pytest.skip("Skipping download tests")
  params = {
    'title': 'richter 10',
    'author': 'Clarke, Arthur C, McQuay, Mike',
    'lang': ['eng'],
    'ext': ['epub']
  }
  response = get('/search', params=params)
  soup = BeautifulSoup(response.text, 'html.parser')
  link = soup.find('a', class_='download')['href']

  print(link)
  response = requests.head(link)

  assert 'Content-Disposition' in response.headers
  value = response.headers['Content-Disposition']
  assert value == 'attachment; filename="Clarke, Arthur C_ McQuay, Mike - Richter 10.epub"'

def test_can_download_fiction_mirrors(client):
  if not config['TEST_DOWNLOAD']:
    pytest.skip("Skipping download tests")
  # This search should have one result for this test to work properly.
  response = get('/search', params={'search': '"axoroad"'})
  soup = BeautifulSoup(response.text, 'html.parser')
  mirrors = soup.select('.mirrors a')
  assert len(mirrors) == 2

  for mirror in mirrors:
    link = mirror['href']
    print(link)
    response = requests.get(link)

    assert_contains(response, 'AxoRoad')
    soup = BeautifulSoup(response.text, 'html.parser')
    a = soup.find('a', string='GET')
    assert a
    link = a['href']
    assert link.startswith("get.php?md5=") or "AxoRoad" in link
