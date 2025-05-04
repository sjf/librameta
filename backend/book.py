import re
import json
import os
import re
from util import nonzero
from mbutils import *

class Book():
  """
  Most the logic for converting the elasticsearch entry to presentation format is here.
  I didn't want the logic in the import pipeline because it is too expensive to re-run
  when the code changes.
  Only the fields used in search like lang and year are processed during import.
  """
  DIR_NAME_REGEX = re.compile('[0-9]+/[a-f0-9]+')

  def __init__(self, hit):
    self.score = hit['_score']
    d = hit['_source']
    self._source = d
    self.id = d['ID']
    self.md5 = d['MD5']
    self.title = d['Title']
    self.volume_info = d['VolumeInfo'] if 'VolumeInfo' in d else ''
    self.series = d['Series']
    self.periodical = d['Periodical'] if 'Periodical' in d else ''
    self._author = d['Author']
    self._year = d['Year']
    self._edition = d['Edition']
    self.publisher = d['Publisher']
    self._pages = d['Pages']
    self._pages_in_file = d['PagesInFile'] if 'PagesInFile' in d else ''
    self.language = d['Language']
    self.issue = d['Issue']
    self.size_in_bytes = d['Filesize']
    self.extension = d['Extension']
    self._identifier_wo_dash = d['IdentifierWODash']
    self.doi = d['Doi'] if 'Doi' in d else ''
    self._cover_path = d['Coverurl'] # This is not a URL, its a file path.
    self.lang3 = d['lang3']

  @property
  def is_nonfiction(self):
    return self.id[0] == 'n'
  @property
  def is_fiction(self):
    return self.id[0] == 'f'
  @property
  def _index(self):
    if self.is_nonfiction:
      return 'main'
    else:
      return 'fiction'

  @property
  def authors(self):
    # semicolon separators
    if ';' in self._author:
      as_ = split(self._author, ';')
    # 'some thing, another thing' looks like comma separator.
    # Contrast with lastname, firstname.
    elif self.is_nonfiction and re.match('[^,]+ [^,]+,[^,]+ [^,]+', self._author):
      as_ = split(self._author, ',')
    else:
      as_ = [self._author]
    as_ = uniq(as_) # Remove duplicates

    result = [ self._build_author(a) for a in as_ ]
    # print(result)
    return result

  def _build_author(self, author):
    author = author.strip()
    display = author
    suffix = ''
    can_link = True

    match = re.match('(.*?)\\s*(\\(.*\\)|et\\.? al\\.?)$', display, re.IGNORECASE) # remove parantheses or 'et al.' from link.
    if match:
      display = match.group(1)
      suffix = ' ' + match.group(2)
    if not display:
      # author contained only the parantheses part e.g. '(editor)'
      can_link = False
      display = author
      suffix = ''

    if re.match('^et\\.? al\\.?$', author, re.IGNORECASE):
      # author was only 'et al', this happens when the string is 'something, et al'.
      can_link = False
    if not author:
      can_link = False

    return {'display': display, 'suffix': suffix, 'link': display, 'can_link': can_link}

  @property
  def pages(self):
    if nonzero(self._pages):
      return f"{self._pages} pages"
    if nonzero(self._pages_in_file):
      return f"{self._pages_in_file} pages"
    return ''

  @property
  def year(self):
    if nonzero(self._year):
      return self._year
    return ''

  @property
  def size(self):
    """ Returns the file size in human readable format."""
    num = self.size_in_bytes
    if num <= 0:
      return ''
    for unit in ("", "Kb", "Mb", "Gb"):
      if num < 1000:
        return f"{num} {unit}"
      num = num//1000
    return ''

  @property
  def isbns(self):
    # this regex should match what the ES tokenizer uses.
    isbns = re.split('[,;:]', self._identifier_wo_dash)
    isbns = map(lambda x:sanitize_isbn(x).upper(), isbns) # remove non-chars
    isbns = filter(lambda x:x, isbns) # remove empty
    isbns = filter(lambda x:re.match('[0-9]+X?', x), isbns) # only return valid ISBNs
    isbns = uniq(isbns) # remove duplicates while preserving order.
    return isbns

  @property
  def _direct_dl_link(self):
    if not config['DIRECT_DL_URL_BASE']:
      return None

    # The destination directory is extracted from the cover path.
    if not self._cover_path:
      return None

    # The directory name and md5 in the direct download link can change between db dumps, but the old
    # link apparently still works.
    dir_name = self._cover_path.split('.')[0].split('-')[0] # remove file extension and the optional -d suffix.
    dir_name = dir_name.lower() # some of the cover paths have uppercase md5, but URL paths are all lower.
    if not Book.DIR_NAME_REGEX.match(dir_name):
      log(f"This book has a wierd cover url: '{self._cover_path}' {self._source}")
      return None

    title = f" - {self.title}" if self.title else ""
    series = f"({self.series}) " if self.series else ""
    periodical = f"({self.periodical}) " if self.periodical else ""
    publisher = f"-{self.publisher}" if self.publisher else ""
    year = f" ({self._year})" if self._year and self._year != '0' else ""
    volume = f". {self.volume_info}" if self.volume_info else ""

    if self.is_nonfiction:
      file_name = f"{periodical}{series}{self._author}{title}{volume}{publisher}{year}"
    else:
      file_name = f"{series}{self._author}{title}"
      dir_name = f"{dir_name}.{self.extension}"
    # Replace chars that cannot be used in filenames.
    file_name = re.sub(r'[<>:"/\\|?*;]', '_', file_name)
    # Truncate.
    file_name = file_name[:200]
    if self.is_nonfiction:
      # Only non-fiction URLs are encoded.
      file_name = url_encode(file_name)

    url=f"{config['DIRECT_DL_URL_BASE']}{self._index}/{dir_name}/{file_name}.{self.extension}"
    return url

  @property
  def _links(self):
    return [ url.format(md5=self.md5, index=self._index) for url in os.environ.get('CDN_URLS').split(',') ]

  @property
  def main_link(self):
    direct_link = self._direct_dl_link
    if not direct_link:
      return self._links[0]
    return direct_link

  @property
  def mirrors(self):
    direct_link = self._direct_dl_link
    if direct_link:
      # Always prefer the first link even though it is
      # using the same hosting as the direct link.
      return self._links
    # First link is used as the direct dl link.
    return self._links[1:]

  @property
  def cover(self):
    if not self.isbns:
      return ''
    return config['COVER_URL'].format(isbn=self.isbns[0])

  @property
  def edition(self):
    edition = self._edition
    if not edition or edition == '0':
      return ''
    if re.match(".*\\W(ed\\.?|edition\\.?)$", edition, re.IGNORECASE):
      return edition
    if re.fullmatch('[0-9]*1', edition):
      edition = f'{edition}st'
    elif re.fullmatch('[0-9]*2', edition):
      edition = f'{edition}nd'
    elif re.fullmatch('[0-9]*3', edition):
      edition = f'{edition}rd'
    elif re.fullmatch('[0-9]+', edition):
      edition = f'{edition}th'
    return edition + " Edition"

  def __repr__(self):
    return f"<Book source:{self._source}>"

def sanitize_isbn(isbn):
  return canonnn(isbn, lower=False, rm_whitespace=True)
