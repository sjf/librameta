#!/usr/bin/env python
import pycountry
import re
import langcodes

# Function to list all languages with their ISO codes and names
def list_all_languages():
    languages = []
    res = {}
    for language in pycountry.languages:
        if hasattr(language, 'alpha_2'):  # Check if the language has a 2-letter code
            name = re.sub('\\(.*\\)','',language.name).lower()
            code = language.alpha_2
            lc = langcodes.get(code)
            native = lc.language_name(lc.language).lower()
            lang_info = {
                'Alpha-2': language.alpha_2,
                'Name': name.lower(),
                'Alpha-3': language.alpha_3 if hasattr(language, 'alpha_3') else None,
                'Native':native,
            }
            languages.append(lang_info)
            #print(language)

            res[code] = lang_info
    return languages,res

def out(code,name,native,code3):
  print(f"WHEN lower(language) = '{name}' THEN '{code}'")
  print(f"WHEN lower(language) = '{code}' THEN '{code}'")
  print(f"WHEN lower(language) like '%{name}%' THEN '{code}'")
  print(f"WHEN lower(language) = '{native}' THEN '{code}'")
  print(f"WHEN lower(language) = '{code3}' THEN '{code}'")


# Get all languages
all_languages,res = list_all_languages()

l = ['en', 'ru', 'zh', 'es',  'hi', 'bn', 'pt', 'ja', 'pnb', 'mr', 'te', 'wuu', 'tr', 'ko', 'fr', 'de', 'vi']
codes = ",".join(map(lambda x:f"'{x}'",res.keys()))
# print(f"""
# ALTER TABLE nonfiction
# ADD COLUMN computed_lang
# enum({codes})
# ;""")
print(f"""
UPDATE nonfiction SET lang = (
CASE
""")
for code in l:
  if not code in res:
    continue
  lang = res[code]
  name = lang['Name']
  code= lang['Alpha-2']
  native = lang['Native']
  code3 = lang['Alpha-3']
  out(code,name,native,code3)

# Print languages

for lang in all_languages:  # Display the first 10 languages
  name = lang['Name']
  code= lang['Alpha-2']
  native = lang['Native']
  code3 = lang['Alpha-3']
  if code in l:
    continue
  if code == "el":
    name = "greek"
  out(code,name,native,code3)

print("""ELSE NULL
END
);""")