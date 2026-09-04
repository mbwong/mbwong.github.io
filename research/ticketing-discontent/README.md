# Event ticketing discontent in Hong Kong — pilot scaffold

A feasibility pilot for a descriptive policy study: what Hong Kong people are
actually aggrieved about in event ticketing, decomposed so that each grievance
maps to an identifiable policy lever.

This directory is research tooling on a working branch. It is not part of the
Hugo site and is not published: Hugo reads `content/`, `data/`, `static/`,
`themes/` and builds to `docs/`, so nothing here reaches mbwong.com.

## Status

The coding pipeline is built and validated end to end on synthetic data.
Collection is not built. Nothing here has touched a real platform.

| Component | State |
|---|---|
| Codebook and coding schema | Built |
| LLM coding harness (sync + batch) | Built, offline-validated, never sent a request |
| Reliability gates (Cohen's kappa) | Built and unit-tested |
| Exhibits E1–E6 | Built, producing output |
| Unit normalisation, hashing, event join | Built |
| Collectors | Not built — see `src/collect/README.md` |
| Survey instrument | Drafted |

The pipeline was developed in an environment whose egress policy denied every
relevant host (`lihkg.com`, `legco.gov.hk`, `consumer.org.hk`, Carousell,
YouTube, `graph.facebook.com`). So the design decision was to build and prove
everything that does not need the network, and to leave collectors unwritten
rather than ship untested code that looks authoritative. Running the pilot for
real is a matter of writing the two Tier A collectors and supplying credentials;
nothing downstream changes.

## The idea in one paragraph

Do not measure "anger about scalping". Decompose grievance by **where in the
ticket allocation pipeline it originates**, because each stage has a different
responsible body and a different lever: pre-public allocation (S1, venue hire
terms and disclosure), the sale mechanism (S2, platform service standards), the
secondary market (S3, the touting offence and its enforcement), post-purchase
(S4, consumer protection), and event day (S5, venue operations). The composition
across those five stages, and how it moves around on-sale dates, is the finding.
`codebook.md` is the full specification.

## Running it

```bash
pip install -r requirements.txt

# 1. Offline validation. No API key, no network. Run this first, and after
#    any change to the codebook or schema.
python tests/test_pipeline.py

# 2. Inspect the exact request payload without sending it.
python src/classify.py --input data/synthetic_pilot.jsonl --dry-run

# 3. Code units. Pilot-scale: sync. Full corpus: --mode batch (half price).
export ANTHROPIC_API_KEY=...
python src/classify.py --input data/units.jsonl --output data/coded.jsonl

# 4. Reliability gates. Must pass before the corpus is coded at scale.
python src/reliability.py --a data/coded_human_A.jsonl --b data/coded_human_B.jsonl
python src/reliability.py --a data/gold.jsonl --b data/coded_model.jsonl --confusion stage

# 5. Exhibits. Pass --units or the grievance clock has nothing to bin on.
python src/describe.py --coded data/coded.jsonl --units data/units.jsonl --outdir exhibits/
```

`data/synthetic_pilot.jsonl` and `data/synthetic_gold.jsonl` are hand-written
fixtures, clearly marked as such in their headers. They exercise every stage,
every stance, the out-of-scope rules, and the two cases the codebook says coders
get wrong (sarcasm that inverts surface sentiment; a scalping complaint whose
grievance originates in allocation). They are test fixtures and must never
appear in an analysis.

## Go / no-go criteria

Decide against these, not against a general impression. Thresholds are set
before seeing data, and the honest outcome of a pilot is sometimes "no".

| | Gate | Threshold | If it fails |
|---|---|---|---|
| G1 | In-scope units from Tier A alone, sweep window | ≥ 2,000 | Stage × time cells too thin. Widen the window or drop E3. |
| G2 | Diffuse share (`S0_DIFFUSE`) | < 0.20 | Taxonomy is not partitioning. Revise the codebook; do not code more. |
| G3 | Human inter-coder kappa on `stage`, n=300 | ≥ 0.70 | Reconcile, amend the codebook, re-run. Never scale on a failed gate. |
| G4 | Model-vs-gold kappa on `stage` | ≥ 0.70 | Try higher effort, then a revised prompt. If it still fails, the corpus is hand-coded and much smaller. |
| G5 | Share of S3 units carrying a stated amount | ≥ 0.10 | Resale premium must come from listings alone. |
| G6 | Consumer Council series separable for ticketing | Yes | External benchmark is weak, and the survey stops being optional. |
| G7 | Meta Content Library approval | Granted | Tier A loses its main text source; the project leans on administrative data and the survey. |

G3 and G4 are the ones that decide whether this is a real measurement exercise
or an expensive way to generate a word cloud. G6 is the one most likely to be
quietly fudged, so check it early: it is a phone call, not a research task.

## Sequencing

Do the cheap decisive things first. Weeks are indicative.

1. **Weeks 0–2.** Administrative and documentary sources: Consumer Council
   counts, the LegCo record, the venue exemption question, police fraud
   statistics, press corpus. Submit the MCL application and the ethics
   application in parallel, since both have external clocks. **G6 resolves
   here, before any money is spent.**
2. **Weeks 2–4.** Build the two Tier A collectors. Pilot-collect. Draw 300
   units and double-code by hand.
3. **Weeks 4–5.** G2–G4. Reconcile, publish codebook v1.0.
4. **Weeks 5–8.** Code the full corpus in batch. Collect resale listings.
5. **Weeks 6–10.** Field the survey. This runs in parallel and is the long pole.
6. **Weeks 10–14.** Exhibits, comparator table, draft.

The comparator table (Hong Kong's penalty and venue exemption against Japan,
Ireland, the UK's announced cap, and the Australian states) needs no data
collection at all and is likely the single most quoted exhibit. It can be
drafted in week 1 and does not depend on any gate.

## Costs

Model coding is not the expensive part. Order of magnitude, with the
assumptions visible so they can be checked rather than trusted:

- Cached system prompt of roughly 1,700 tokens, a short unit, and roughly 300
  output tokens per unit.
- At Opus 5 rates that is on the order of US$0.01 per unit at full price, less
  with the system prompt cached, and half again in batch mode.
- A 50,000-unit corpus therefore lands in the low hundreds of US dollars, not
  thousands.

Measure this properly on the pilot: `classify.py` records `input_tokens`,
`output_tokens` and `cache_read_input_tokens` per unit for exactly that purpose.
If `cache_read_input_tokens` is zero across a run, caching is silently broken
and the cost estimate is roughly ten times off.

Before settling on a model, sweep `--effort low` and `--effort medium` against
the gold set and read the kappa. Buy the cheapest configuration that clears G4,
and report which one was used.

The real budget lines are the survey panel, RA time, and any data enclave fee.
Price those against HKU rates rather than assuming.

## What this design cannot do

Stage shares describe the composition of expressed grievance among people who
post. They are not prevalence in the Hong Kong population. No amount of
additional scraping fixes this; only the survey does. The distinction belongs in
the body of any report, not buried in an appendix, and it is the first thing a
serious referee or a sceptical official will press on.

Two further limits worth stating plainly. The venue contrast (LCSD-exempt versus
other) is an institutional classification, not a randomised assignment, so it
supports description and not a causal estimate. And selection into real-name
registration is not random, since high-demand shows adopt it, so that contrast
is suggestive at best.

## Legal and ethical

Publicly accessible personal data is still personal data under the PDPO, and the
statistics-and-research exemption is narrow, conditional, and argued case by
case rather than assumed. Human research ethics approval precedes collection.
Author identifiers are salted-hashed at the point of collection, with the salt
stored outside this repository. Exhibits are aggregate; no verbatim quote that
could identify an individual is published. `src/collect/README.md` carries the
per-source rules.

## Facts to verify before publication

These shaped the design and came from secondary sources. Each needs a primary
citation before it appears in anything public.

- The Cap. 172D exemption order and its effect on LCSD-managed venues, checked
  against the legislation itself. This is the paper's central legal claim.
- The maximum penalty under the touting offence, and the conviction record.
- The widely repeated claim that only 20–30% of tickets reach public sale. This
  is a media figure. Source it properly or drop it; do not launder it through a
  citation to a news article.
- Meta Content Library's current fee, retrieval cap, and field list, especially
  whether any author demographic field exists.
