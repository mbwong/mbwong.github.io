#!/usr/bin/env python3
"""
Offline tests for the parsing logic in the audit scripts.

These do NOT touch the network. They pin down the pure functions against
synthetic fixtures shaped like the real pages, so that when the scripts are
finally run against live endpoints the only thing that can be wrong is the
page layout, not the logic.

Run: python test_parsers.py
"""

import importlib.util
import re
import sys


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hklii = load("02_hklii_census.py", "hklii")
legco = load("03_legco_enforcement.py", "legco")
wayback = load("01_wayback_coverage.py", "wayback")

failures = []


def check(name, got, want):
    if got == want:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n        got  {got!r}\n        want {want!r}")
        failures.append(name)


print("judgment_links")
INDEX = """
<html><body>
  <a href="/en/cases/hkdc/2019/1234">HKSAR v Chan [2019] HKDC 1234</a>
  <a href="/en/cases/hkdc/2019/1235?query=x">HKSAR v Lee</a>
  <a href="/en/cases/hkdc/2019/1234">duplicate link</a>
  <a href="/en/legis/ord/200">Crimes Ordinance</a>
  <a href="/about">About</a>
</body></html>
"""
check("extracts + dedupes + strips query",
      hklii.judgment_links(INDEX, "https://www.hklii.hk/en/cases/hkdc/2019/"),
      ["https://www.hklii.hk/en/cases/hkdc/2019/1234",
       "https://www.hklii.hk/en/cases/hkdc/2019/1235"])
check("empty index yields nothing",
      hklii.judgment_links("<html></html>", "https://x/"), [])

print("\noffence patterns")
P = hklii.OFFENCE_PATTERNS
check("vice establishment",
      bool(P["vice_establishment"].search(
          "convicted of keeping a Vice Establishment contrary to s.139")), True)
check("living on earnings (with 'the')",
      bool(P["living_on_earnings"].search(
          "charged with living on the earnings of prostitution of another")), True)
check("living on earnings (without 'the')",
      bool(P["living_on_earnings"].search(
          "living on earnings of prostitution")), True)
check("procuring near prostitution",
      bool(P["procuring"].search(
          "did procure the complainant to become a prostitute")), True)
check("soliciting",
      bool(P["soliciting"].search(
          "soliciting for an immoral purpose in a public place")), True)
check("no false positive on unrelated text",
      any(p.search("a contract dispute about a restaurant lease")
          for k, p in P.items()), False)

print("\nextract_tables")
REL = """
<html><body>
<p>LCQ5: Combating illegal prostitution</p>
<table>
  <tr><th>Year</th><th>Keeping a vice establishment</th></tr>
  <tr><td>2013</td><td>412</td></tr>
  <tr><td>2014</td><td>388</td></tr>
</table>
<table><tr><td>only one row</td></tr></table>
</body></html>
"""
tables = legco.extract_tables(REL)
check("keeps the >=2-row table only", len(tables), 1)
check("header row parsed", tables[0][0], ["Year", "Keeping a vice establishment"])
check("data rows parsed", tables[0][1:], [["2013", "412"], ["2014", "388"]])

print("\ntitle hints")
check("matches LCQ vice title",
      bool(legco.TITLE_HINTS.search("LCQ5: Combating illegal prostitution")), True)
check("matches vice establishment title",
      bool(legco.TITLE_HINTS.search("LCQ11: Vice establishments in residential buildings")), True)
check("ignores unrelated release",
      bool(legco.TITLE_HINTS.search("LCQ3: Cross-harbour tunnel tolls")), False)

print("\nwayback id extraction")
default_re = re.compile(r"/(\d{4,})")
urls = ["http://sex141.com/girl/123456/",
        "http://sex141.com/girl/123456?ref=a",
        "http://sex141.com/about",
        "http://sex141.com/girl/999888/"]
ids = [default_re.search(u).group(1) for u in urls if default_re.search(u)]
check("pulls stable numeric ids", ids, ["123456", "123456", "999888"])
check("hashing is stable within a run",
      wayback.hid("123456"), wayback.hid("123456"))
check("hashing separates distinct ids",
      wayback.hid("123456") == wayback.hid("999888"), False)
check("hash leaks no digits of the id",
      "123456" in wayback.hid("123456"), False)

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("all parser tests passed")
