# Survey instrument (Tier D), draft v0.1

The survey exists to do the one thing the scraped corpus cannot: support
statements about the Hong Kong population rather than about people who post.
Every population-level claim in the final report should trace to this
instrument; every composition claim traces to the corpus. Keeping that line
clean is the main methodological discipline of the project.

**Target:** n ≈ 1,200, online panel, quota-sampled to census age × gender ×
district. Median completion 8 minutes.

**Screening logic:** everyone answers Blocks A and D. Only respondents who
attempted to buy a ticket in the reference period answer B and C. This is what
lets incidence be computed on a defined denominator.

---

## Block A — Exposure and denominator (all respondents)

A1. In the last 24 months, did you try to buy a ticket to a concert, show, or
major sporting event in Hong Kong?
`Yes / No / Don't recall`

A2. *(if yes)* Roughly how many separate on-sales did you try for?
`1 / 2-3 / 4-6 / 7+`

A3. *(if yes)* For the most recent one, did you succeed in buying at the
original price?
`Yes / No, bought above original price / No, did not buy / Bought but later
could not use it`

A4. *(if no to A1)* Was any of the following a reason you did not try?
*(multi-select)* `Expected not to get tickets / Prices too high / Process too
difficult / Not interested in any event / Other`

> A4 matters more than it looks. Discouraged non-participation is invisible in
> scraped data and is a real welfare cost. If it is large, it belongs in the
> report's headline.

## Block B — Incidence by pipeline stage (buyers only)

B1. Thinking about your ticket attempts in the last 24 months, did you
experience each of the following? `Yes / No / Not sure`

| | Stage |
|---|---|
| a. Found that very few tickets seemed available to the general public | S1 |
| b. The website or app failed, timed out, or crashed during the sale | S2 |
| c. Tickets sold out so fast you believe bots or insiders were involved | S2/S1 |
| d. Bought from a reseller above the original price | S3 |
| e. Were scammed or received an invalid ticket in a private resale | S3 |
| f. Ticket was wrong, or a refund or exchange was refused | S4 |
| g. Problems at entry, including identity verification | S5 |

B2. Which of those was the **most** serious for you? `single choice from B1 list
/ none were serious`

> B1 gives incidence per stage. B2 gives a forced ranking directly comparable to
> the corpus's primary-stage distribution. That comparison is the validation
> exercise the whole design turns on: if the corpus and the survey rank the
> stages the same way, the corpus can be read as informative about composition
> despite being non-representative. If they diverge, that divergence is itself
> the most interesting finding in the paper, and it should be reported as such
> rather than explained away.

B3. *(if B1d)* How much above the original price did you pay, in total?
`Under HK$500 / $500-1,999 / $2,000-4,999 / $5,000-9,999 / $10,000+ /
Prefer not to say`

B4. *(if B1e)* Approximately how much did you lose? *(same bands)*

B5. Did you complain to anyone? *(multi-select)* `The ticketing platform / The
organiser / Consumer Council / Police / Posted publicly on social media /
Told friends only / Did not complain`

> B5 is the bridge between the survey and both other data sources. The share
> who post publicly is the selection rate into the scraped corpus; the share who
> complain formally is the selection rate into the Consumer Council counts. Both
> denominators are otherwise unobservable, and without them neither series can
> be read as a level.

## Block C — Attribution (buyers only)

C1. Who is most responsible for the problems you experienced?
`The ticketing platform / The event organiser or promoter / Scalpers and
resellers / The Government / Other fans / Nobody in particular`

C2. How much do you agree: "The Government has the power to fix these problems
if it chooses to." `5-point agree-disagree`

C3. How much do you agree: "How tickets are allocated before public sale is
transparent." `5-point agree-disagree`

## Block D — Policy preferences and fairness (all respondents)

D1. Support or oppose each: `5-point support-oppose`
 a. Capping resale at the original price
 b. Capping resale at the original price plus a small margin
 c. Criminal penalties for large-scale touting
 d. Requiring organisers to disclose how many tickets go on public sale
 e. Mandatory real-name registration for high-demand events
 f. Requiring refunds when an event is postponed

D2. Some argue resale markets help by moving tickets to those who value them
most. Others argue they are unfair. Which is closer to your view?
`Efficiency view / Fairness view / Both equally / Neither`

D3. *(split-ballot)* Randomly assign one vignette:
 - **V1:** a ticket resold at four times face value to a buyer who wanted it more
 - **V2:** a ticket allocated through a sponsor's internal quota, never on public sale

"How fair is this?" `5-point`

> D3 is the only experimental element and it is cheap. It tests whether the
> public objects to high prices as such, or to opaque allocation. Those two
> readings point to different policies, a price cap versus a disclosure rule,
> and the corpus cannot distinguish them because both grievances use the same
> angry vocabulary. If respondents rate the quota vignette as less fair than the
> markup vignette, the disclosure lever gains a constituency the debate has not
> noticed.

## Block E — Demographics

Standard: age, gender, district, education, household income band, employment
status, and whether the respondent regularly attends live events. Income bands
must match a census or GHS classification so the sample can be reweighted and
compared.

---

## Analysis commitments, fixed before fielding

1. Primary outcome is stage-level incidence (B1) on the A1 denominator.
2. The corpus-versus-survey stage-ranking comparison (B2 against E1) is
   specified in advance, and reported whichever way it comes out.
3. Subgroup analyses limited to age, income, and attendance frequency. Any
   other cut is exploratory and labelled as such.
4. The instrument, the quotas, and these commitments are registered before
   fielding. Descriptive work is not exempt from pre-registration; it is where
   pre-registration is cheapest.
