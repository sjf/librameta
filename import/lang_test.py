import pytest
from lang import *

lang_codes = [
    ("English", "eng"),
    ("Russian", "rus"),
    ("Arabic", "ara"),
    ("русский", "rus"),
    ("עברית", "heb"),
    ("Uighur", "uig"),
    ("اردو", "urd"),

    ("ru", "rus"),
    ("Russian", "rus"),
    ("eng","eng"),
    ("en","eng"),
    ("fra", "fra"),
    ("fra,eng", "eng"),
    ("es_ES", "spa"),


    ("Greek(Modern)", "ell"),
    ("Russian(Old)", "rus"),
    ("Greek, Modern (1453-)", "ell"),
    ("Arabic (Eastern)", "ara"),
    ("Portuguese(Portugal)", "por"),
    ("Portuguese Brazilian", "por"),
    ("Bengali (বাংলা)", "ben"),

    ("English-Russian", "eng"),
    ("German-English", "eng"),
    ("Dutch; Flemish", "nld"),
]

@pytest.mark.parametrize("input, expected", lang_codes)
def test_get_langcode(input, expected):
  assert get_langcode(input) == expected

no_years = [
  "",
  "0",
  "No years here.",
  "123",
  "01/02/93",
  "19-93",
  "",
  "0100",
  "200u/9999",
  "2055"
]
years = [
    ("1990", 1990),
    ("[1956?]", 1956),
    ("1993;1997", 1993),
    ("2005-2010", 2005),
    ("2003-01-01", 2003),
    ("19/2/1770", 1770),
    ("1982 (2009)", 1982),
    ("1939\u20141930", 1930),
    ("2011,2005,2003", 2003),
    ("2021June 15", 2021),
    ("2014März 3", 2014),
    ("۱۳۸۷", 1387),
    ("১৪২৭.", 1427),
    ("2001年1月1日", 2001),
]

@pytest.mark.parametrize("input", no_years)
def test_get_year_negative(input):
  assert get_year(input) is None

@pytest.mark.parametrize("input, expected", years)
def test_get_year(input, expected):
  assert get_year(input) == expected

