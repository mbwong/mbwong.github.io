# Codebook: Event Ticketing Discontent in Hong Kong

Version 0.1 (pilot). Every change to this file must bump the version, because the
version string is written into every coded record and drives reconciliation.

## 1. Unit of analysis

One **post or top-level comment**. Replies nested under a comment are separate
units. Threads are not units; a thread's grievance profile is the aggregate of
its units.

Exclusion rules, applied before coding:

- Not about ticketing for a live event in Hong Kong (drop).
- Pure resale advertisement with no expressed grievance (drop from the grievance
  corpus, but retain in the resale-listing corpus, which is coded separately).
- Non-substantive (single emoji, "+1", quote with no added text) (drop).
- Duplicate text from the same author within 24 hours (keep first).

## 2. Primary dimension: pipeline stage

Each unit is assigned **exactly one** primary stage, the stage where the
grievance originates. Where a unit expresses grievances at several stages, code
the primary stage as the one the author spends the most text on, and record the
others in `secondary_stages`. This forced-choice-plus-secondary design is what
lets stage shares sum to one while preserving multi-grievance texture.

| Code | Stage | Grievance content | Policy lever |
|---|---|---|---|
| `S1_ALLOCATION` | Pre-public allocation | Internal/sponsor/fan-club/credit-card quotas; how few tickets reached public sale; opacity about the split | LCSD venue hire terms; disclosure requirements |
| `S2_SALE` | Sale mechanism | Queue collapse, site down, timeouts, payment failure, bots, "sold out in seconds", CAPTCHA and login failures | Platform procurement and service standards (Urbtix, Cityline) |
| `S3_SECONDARY` | Secondary market | Touting, markups, resale platforms, ticket scams and fraud | Cap. 172 / Cap. 172D; Police enforcement |
| `S4_POSTPURCHASE` | Post-purchase | Ticket errors, wrong tier printed, refund refusal, cancellation terms, restricted view not disclosed, fees | Consumer Council; Trade Descriptions Ordinance |
| `S5_EVENTDAY` | Event day | Entry queues, real-name ID verification friction, denied entry, venue crowd management | Venue operators; LCSD |

`S0_DIFFUSE` is available for units that are clearly about ticketing discontent
but name no stage ("HK concert ticketing is a joke"). Track its share; if it
exceeds 20% the taxonomy is failing and needs revision, not more coding.

## 3. Secondary fields

- `secondary_stages`: list, possibly empty, of other stages present.
- `attribution`: who the author blames. One of `GOVERNMENT` (LCSD, the Bureau,
  mega-event policy, "官"), `PLATFORM` (Urbtix, Cityline, Klook, Trip.com),
  `PROMOTER` (organiser, artist's company), `SCALPER`, `OTHER_FANS`,
  `NONE`. This is the field that carries most of the political-economy insight,
  so code it conservatively: `NONE` unless blame is explicit.
- `affect`: `GRIEVANCE` (complaint), `RESIGNATION` (expects nothing better),
  `MOBILISATION` (calls for action, petition, complaint to Consumer Council),
  `DEFENCE` (defends the system or operator). Not a sentiment score; these are
  distinct stances with different policy meanings.
- `remedy_named`: boolean, whether the author names a concrete fix (real-name
  ticketing, price cap, quota disclosure, criminal penalty).
- `event_ref`: free text naming the event/artist/venue if identifiable, else null.
- `money_claim_hkd`: numeric if the author states a specific price, markup, or
  loss, else null. Powers the resale-premium exhibit.
- `first_person`: boolean, whether the author claims direct personal experience
  as opposed to commenting on reports. Separates experienced harm from ambient
  opinion, which matters because only the former speaks to incidence.

## 4. Language handling

The corpus is majority written Cantonese with heavy code-mixing, plus
traditional-character standard Chinese and English. Coders and the model see the
raw text with no translation or normalisation. Romanised Cantonese, LIHKG slang,
and homophone evasion are in scope and must not be "cleaned".

Known trap: Cantonese negation and sarcasm invert surface sentiment routinely
("好嘢又係內部飛" is a grievance, not praise). Any classifier that scores this
corpus with a general-purpose Chinese sentiment model will be wrong in a
direction that correlates with the outcome. This is why `affect` is a
categorical stance judgement, not a sentiment score.

## 5. Reliability protocol

1. Two human coders independently code the same random sample of 300 units.
2. Compute Cohen's kappa per field. Thresholds for proceeding: kappa >= 0.70 on
   `stage`, >= 0.60 on `attribution` and `affect`.
3. Reconcile disagreements, and amend this codebook where a disagreement
   reveals an ambiguous rule rather than a coder error. Bump the version.
4. The reconciled 300 become the **gold set**.
5. The model codes the gold set blind. Model-vs-gold kappa on `stage` must reach
   >= 0.70 before the model is used on the full corpus. Report this number in
   any publication; it is the validity claim.
6. Re-audit: draw 100 model-coded units per 5,000 and re-check by hand. Drift in
   these audits is reported, not silently corrected.

## 6. What this codebook cannot support

Stage shares describe **the composition of expressed grievance among people who
post**. They are not prevalence in the Hong Kong population and must never be
written up as such. Population-level statements require the survey instrument in
`survey/`. This limitation belongs in the paper, not only in the appendix.
