import pytest
from es import *

queries = [
  ("", "", []),
  ("'",  "'", []),
  ('"', "", []),
  ("''", "''", []),
  ('""', "", []),

  ("a b c", "a b c", []), # no quotes
  ("a's b'c d'f", "a's b'c d'f", []), # single quotes do nothing

  # separates doubled quoted strings
  ('foo "bar buz" bux', "foo bux", ['bar buz']),
  ('a "b c" d e "f . | & g" h | & ; a', "a d e h | & ; a", ['b c', 'f . | & g']),
  ('"a b c"', "", ['a b c']),

  # unmatched quote quotes to end of string
  ('"a b c', "", ['a b c']),
  ('a b c "d \'e', "a b c", ['d \'e']),
  ('a b c "d e"" f', "a b c", ['d e', ' f']),

  # cant escape quotes
  ('a \\" b', 'a \\" b', []),
  ("a \\' b", "a \\' b", []),
]

@pytest.mark.parametrize("input, unquoted, quoted", queries)
def test_get_quoted_substrings(input, unquoted, quoted):
  u,q = get_quoted_substrings(input)
  assert unquoted == u
  assert quoted == q
