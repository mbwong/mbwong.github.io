# Wisers / WisersOne search strategy

Search strings are part of the method, not scratch work. Record every query
verbatim with the date run, the source filter, the date range, and the hit
count. A referee should be able to reproduce the corpus from this file alone.

Two notes before running anything:

**Verify the operator names in the database rather than trusting this file.**
Search the English name first (`Cityline`, `URBTIX`) and read how the HK press
actually renders it in Chinese, then use that form. The renderings below are
my best understanding and are the most likely thing here to be wrong.

**Hit counts are themselves data.** Running the same query per month and
recording only the number of articles gives a media-salience time series
without exporting a single article. That series survives even if the licence
turns out to forbid bulk export, so capture it on the first pass regardless of
what you later learn about text-and-data-mining rights.

---

## Search 1 — Event chronology

Purpose: populate `data/events.template.json` with sourced on-sale dates. This
is the blocking dependency for the E3 grievance clock, which currently cannot
run because I would not invent dates.

```
(演唱會 OR 音樂會 OR 騷) AND (公開發售 OR 售票 OR 開賣 OR 訂飛)
```

Narrow by venue to build the calendar venue by venue:

```
紅館 OR 香港體育館 OR 啟德體育園 OR 啟德主場館
伊利沙伯體育館 OR 香港大球場 OR 亞洲國際博覽館
```

Capture per event: artist, venue, on-sale date, on-sale time, whether
real-name registration applied, and the article as the citation.

## Search 2 — Policy and legal track

Purpose: the comparator table and the venue-exemption argument. Needs no
coding pipeline and is publishable on its own.

```
(炒賣 OR 炒飛 OR 黃牛) AND (立法會 OR 政府 OR 條例 OR 修例 OR 執法)
公眾娛樂場所條例
(康文署 OR 文化體育及旅遊局) AND (門票 OR 售票 OR 炒賣)
實名制 AND (門票 OR 演唱會)
```

Watch for: the Cap. 172D exemption, the maximum penalty, prosecution and
conviction counts, and any consultation or bill. These are the facts flagged
in the README as needing primary citation.

## Search 3 — Sale mechanism failures (stage S2)

```
(售票網 OR 購票 OR 訂飛) AND (死機 OR 癱瘓 OR 塞爆 OR 排隊 OR 輪候 OR 故障)
(城市售票網 OR 購票通 OR 快達票) AND (投訴 OR 問題 OR 故障)
撲飛 AND (失敗 OR 撲空)
```

`城市售票網` is URBTIX; `購票通` is Cityline; `快達票` is HK Ticketing.
Confirm each in the database before relying on it.

## Search 4 — Secondary market (stage S3)

```
(黃牛飛 OR 黃牛票 OR 黃牛黨 OR 炒飛 OR 炒票 OR 炒家) AND 香港
(門票 OR 演唱會) AND (天價 OR 高價 OR 加價 OR 轉售)
(演唱會 OR 門票) AND (騙案 OR 詐騙 OR 呃錢 OR 假飛)
```

The fraud strand matters: ticket scams are a distinct harm from markup and a
distinct policy lever (Police rather than the touting offence). Keep them
separable in the coding.

## Search 5 — Allocation and consumer protection (stages S1, S4)

```
(內部認購 OR 內部飛 OR 贊助商 OR 預售 OR presale) AND (門票 OR 演唱會)
公開發售 AND (比例 OR 成數 OR 透明)
(消費者委員會 OR 消委會) AND (門票 OR 演唱會 OR 售票)
(門票 OR 演唱會) AND (退票 OR 退款 OR 改期 OR 延期)
```

The second line is aimed squarely at the disputed 20–30% public-sale claim.
Find where that figure originates before citing or discarding it.

## Search 6 — Mega-event framing

Purpose: the political-economy layer, and the attribution question of whether
ticketing failure attaches to government policy or to private operators.

```
(盛事經濟 OR 盛事之都 OR 大型盛事) AND (門票 OR 售票 OR 黃牛)
```

## English-language HK press

For SCMP, HKFP, The Standard, and wire copy:

```
(ticket) AND (scalping OR touting OR tout OR resale OR reseller)
(Coliseum OR "Kai Tak") AND ticket
"real-name" AND ticket
"Consumer Council" AND (ticket OR concert)
```

---

## Traps

- **Never search `飛` alone.** It means "fly" as well as "ticket" and will
  drown the corpus. It is only usable inside a compound (`撲飛`, `黃牛飛`,
  `訂飛`) or paired with a venue or event term.
- **Restrict sources to Hong Kong on the first pass.** The database also
  covers the mainland, Macau and Taiwan, all of which have their own ticketing
  controversies that will contaminate counts.
- **Check whether the interface folds simplified and traditional characters
  together.** If it does not, run both forms and say so in the methods.
- **Suggested window: 2018 to present.** That reaches back to the earlier
  LegCo cycle on touting and spans the MIRROR real-name episode and the
  post-2023 mega-event push, so trend claims have a baseline. Extend earlier
  only if the salience series looks censored at the left edge.
- **De-duplicate wire copy.** The same agency story runs in many outlets and
  will inflate any count. Decide the rule before counting, not after seeing
  the numbers.
