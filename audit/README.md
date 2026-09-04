# Feasibility audit: Hong Kong sex market data

Status as of 2026-09-04. Read the "Blocked" section first: two of the four
audit steps could not be executed in this environment, and they are the two
that decide whether the project lives.

---

## Blocked, and why

This session had no outbound network egress. Every relevant host returned
403 at the proxy CONNECT stage, including `web.archive.org`, `www.hklii.hk`,
`www.legco.gov.hk`, `www.info.gov.hk`, `www.police.gov.hk`, `data.gov.hk`,
and `legalref.judiciary.hk`. The block is blanket rather than
subject-specific: `en.wikipedia.org` was refused identically. Only
search-engine queries, which run server-side, went through.

So audit steps 1 and 2 are **unresolved**, and steps 3 and 4 are established
only as far as search snippets allow. The scripts here execute all four the
moment egress exists. To unblock, allowlist those hosts in the environment's
network policy (see the Claude Code on the web docs on environments), or run
the scripts on a local machine, where they need only `pip install requests
beautifulsoup4`.

Nothing below is inferred from the scripts having run. They have not run
against live endpoints. Their parsing logic is unit-tested offline
(`test_parsers.py`, 18 assertions, all passing); their selectors are not
verified against real pages and should be expected to need fixing on first
contact.

---

## Established

**The platform is real and named.** Sex141, established 2002, is described in
public sources as the most active sex-work advertising and information
network in Hong Kong. This is no longer a hypothesis about "a 141 ecosystem";
it is a specific site with a documented history, which also means it has a
documented *pre-2020* history worth probing in the archive.

**Prior art exists but is qualitative.** There is a study titled "Online
Platforms for Female Sex Workers in Hong Kong: A Qualitative Analysis of
Advertisements and Customer Reviews." This cuts two ways. It means the
quantitative lane is genuinely open, and it means somebody has already got
research access to this material through an ethics committee, which is
useful precedent to cite in your own application. It also means a referee
will ask what you add beyond it, so the answer cannot be "more observations."

**The enforcement panel exists at the right granularity.** LCQ5 "Combating
illegal prostitution" (28 October 2015) carries an Annex 1 giving persons
arrested for *procuring/controlling of prostitution* and *keeping a vice
establishment* over the preceding five years, i.e. broken out by offence
type. A 2004 LegCo Panel on Security paper separately reports 700+ detected
cases of managing a vice establishment and living on the earnings of
prostitution across an eight-month window. Annual counts in the hundreds,
split by offence, is workable variation for an event study. Every such reply
is mirrored verbatim on `info.gov.hk`, which is what `03_legco_enforcement.py`
harvests.

**HKLII is structurally scrapable.** Judgments are path-organised by court and
year (`/en/cases/hkdc/`, `/en/cases/hkca/`, `/en/cases/hkcfi/`,
`/en/cases/hkcfa/`), free, and cover 1946 onward for the trial courts. No
public API or bulk-download facility surfaced in search, so plan on polite
crawling. `02_hklii_census.py` does this.

**Independent ground truth exists.** Hong Kong runs serious behavioural and
HIV surveillance on this population: 407 street-based female sex workers in
one health-services study, 5,294 cross-border male clients across four
border-checkpoint surveys 1997-2001, and a 2019 HARiS round with 398 male
clients of female sex workers, published via `aids.gov.hk`. This matters more
than it looks. It gives you an external validation sample for whatever the
scraped listings say, and the client-side surveys are a demand-side series
you can use independently. Most papers in this literature have no such
benchmark.

**The legal exposure is confirmed and specific.** The Personal Data (Privacy)
(Amendment) Ordinance 2021 took effect 8 October 2021. It creates a two-tier
offence for disclosing personal data without consent where the discloser
intends or is reckless as to causing specified harm, with the second tier an
indictable offence where harm results, and gives the Privacy Commissioner
criminal investigation and prosecution powers plus cessation-notice powers.
This is a real constraint on holding identifiable data about this population
in Hong Kong, not a formality.

---

## Unresolved, and decisive

These two are the whole ballgame. Run `01_wayback_coverage.py` first.

1. **Does the archive hold pre-2020 snapshots?** If not, the border-closure
   design is dead. Adult sites are frequently excluded from the Wayback
   Machine by robots rules or takedown, so a null result here is entirely
   possible and you should want to know it in the first hour, not the third
   month.

2. **Can the same listing be observed across months?** The script answers
   this from capture metadata alone, without downloading any listing content,
   by extracting stable numeric IDs from archived URLs and tabulating the
   distribution of distinct months per ID. It also uses the CDX `digest`
   field to measure how often a listing's content *changed* between captures,
   a proxy for price and menu revisions, again without seeing what it said.
   Above roughly 30% of IDs observed in two or more months, you have a panel.
   Below that, you have a repeated cross-section, and designs 2 and 3 collapse
   to something much weaker.

---

## Revised recommendation

The four framings in the original scoping note were generic. Having read the
publication list in this repo, the strongest paper here is a different one.

Hong Kong does not merely regulate this market. It **criminalises
intermediation while leaving the underlying transaction legal**. Living on
the earnings of prostitution is the intermediary's rent. Keeping a vice
establishment is the firm. Procuring is the matching function. All three are
offences; the transaction itself is not. The "one woman, one flat" rule is
the enforcement technology that makes the ban bite, and it forces the market
into exactly the decentralised structure that the alternative would not take.

That is the empirical counterpart to *Managerial Coordination in
Decentralized Markets* (EJ 2026). The model there asks when buyers contract
through an intermediary that aggregates fluctuating demand, lengthens
relationships and monitors performance, versus contracting directly, and
predicts that intermediation raises job security, compresses pay variance,
expands trade, and shifts surplus from producers to buyers. Hong Kong bans
the intermediary and lets the direct market operate. The listing platforms
are then precisely the "digital matching platforms" the paper gestures at,
arriving as a partial substitute for the coordination the law destroyed.

So the question becomes: *what does a matching platform restore, and what can
it not restore, when managerial coordination is illegal?* That is a paper only
you can write, it uses a setting you already have institutional command of
(RSUE 2026 is Hong Kong administrative data), and it does not depend on
out-competing Cunningham and Kendall on sample size, which is not a fight
worth having.

It also degrades gracefully. If step 2 shows no panel, the intermediation
question survives on court records alone: judgments under s.137 and s.139
describe the banned organisational forms in detail, including rents, takings,
recruitment, and structure. That is `02_hklii_census.py`, it needs no
adult-site scraping at all, and it clears an ethics review quickly.

Decision rule for that fallback: 200 or more judgments with substantive facts
supports a standalone paper on court records; under 50 means judgments are a
supplement rather than a foundation.

One caveat to carry into the design: magistrates' courts handle most vice
prosecutions and largely do not publish written judgments, so the HKLII
corpus is selected toward the more serious and more organised end. That
selection is a limitation for a prevalence claim, but it is close to
harmless, possibly even helpful, for a paper about organisational form.

---

## Running it

```bash
pip install -r requirements.txt
python test_parsers.py                                   # offline, no network

python 01_wayback_coverage.py --domain sex141.com        # run this first
python 02_hklii_census.py --mode crawl --court hkdc --from 2005 --to 2025
python 03_legco_enforcement.py --from 2015 --to 2015     # smoke test one year
python 03_legco_enforcement.py --from 2005 --to 2026     # full harvest
```

Scripts 2 and 3 cache every fetch to `.cache_hklii/` and `.cache_gia/`, so
reruns are cheap and a crash costs nothing. Both are rate-limited. Output
lands in `out/`. Caches and outputs are gitignored.

## Handling rules baked into these scripts

- Script 1 downloads **no** listing content, only capture metadata.
- Listing IDs are salted-hashed before touching disk; set `AUDIT_SALT` for
  reproducibility across runs, leave it unset for throwaway audits.
- No photos, aliases, or contact details are collected by anything here.
- Aggregate to building-month before any analysis, and never publish or share
  a raw scrape.

If the project proceeds past the audit, treat the PDPO position above as
something to check with a Hong Kong qualified lawyer rather than something
settled by this document, and think hard about the exposure of any coauthor
or RA physically in Hong Kong before they touch collection.
