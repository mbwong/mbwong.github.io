# Collectors

Each collector's only job is to emit records shaped
`{id, author_id, posted_at, text, thread_title?, url?}` and hand them to
`normalise.normalise()`. Nothing downstream knows which platform a unit came
from except through the `source` field.

No collector is included here as working code, and that is deliberate: none
could be executed or tested in the environment this scaffold was built in, and
an untested collector that looks authoritative is worse than an honest gap.
What follows is the access position for each source as of the pilot design, so
whoever writes them starts from the right assumptions rather than rediscovering
them.

## Tier A: the backbone

### Meta Content Library (Facebook, Instagram, Threads)

The only route with real Hong Kong coverage that is unambiguously permitted for
academic use. Access is by application through Meta's researcher process and
takes roughly 2 to 6 weeks; approval is required before any code is worth
writing.

Confirm before budgeting, because these numbers move and were taken from
secondary summaries rather than Meta's own documentation:

- whether the enclave fee applies to this project and at what rate
- the current per-researcher retrieval cap and whether UI exports count against it
- **whether author-level demographic fields exist at all.** The documented
  metadata is engagement counts, page and group metadata, geographic location of
  Page admins, and hashed user IDs. Plan on no author age or gender. The hashed
  user ID is the field that matters most here: it is what makes the
  within-author panel possible.

Analysis runs inside Meta's environment under their terms. Design the exhibits
so that what leaves the enclave is aggregate.

### YouTube comments

Comments on Hong Kong news coverage of ticketing controversies. The Data API's
`commentThreads` endpoint is permitted and free within a daily quota, which
makes this the cheapest legitimate text in the project. Quota is the binding
constraint on how many videos can be swept, so select videos deliberately from a
press corpus rather than crawling broadly.

### Resale listings

The quantitative core of the project: stated asking prices convert grievance
into a money number. Check the platform's terms and `robots.txt` before writing
anything, prefer any official or licensed feed, and rate-limit conservatively.
Listings are coded on a separate schedule from grievance units; a listing is not
a complaint, and the codebook excludes it from the grievance corpus.

### Administrative and documentary sources

Consumer Council complaint counts, LegCo questions and research briefs, police
fraud statistics, and a Chinese-language press corpus via the university's
Wisers or Factiva subscription. These are not scraped; they are read and
transcribed, and they carry the external benchmark that makes the scraped
composition interpretable. Do this part first. It is the cheapest work in the
project and it determines whether the rest is worth doing.

## Tier B: texture, non-representative

### LIHKG

Highest density of exactly this complaint genre, and the worst access position:
CAPTCHA-protected, rate-limited, no sanctioned API, and a user base that is
young, male and politically distinctive. Existing academic scrapers take a
semi-manual approach. Use it for the complaint taxonomy and mechanism narrative,
label it non-representative wherever it appears, and never let it carry a
prevalence claim.

## Not recommended

**X** has no academic tier, is now pay-per-use, and has thin Hong Kong
penetration for consumer complaints. **Xiaohongshu** matters substantively for
the mainland-buyer view but has no official API, aggressive anti-scraping,
ToS exposure through cookie-based access, and PRC data-law exposure on top of
the PDPO. If the mainland perspective is needed, reach it through the survey or
through press coverage, not through scraping.

## Rules that bind every collector

1. Public does not mean unregulated. Publicly accessible personal data is still
   personal data under the PDPO, and the research exemption is narrow,
   conditional, and must be justified case by case rather than assumed.
2. Hash author identifiers at the point of collection, with a salt stored
   outside this repository. Raw handles never enter the analysis files.
3. Never publish verbatim quotes that could identify an individual. Exhibits are
   aggregate; illustrative quotes must be paraphrased and stripped of detail.
4. Human research ethics approval before collection begins, not after.
5. Respect `robots.txt` and rate limits even where doing so costs coverage. A
   coverage gap is a footnote; a terms breach is a retraction.
