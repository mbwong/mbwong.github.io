"""Offline end-to-end check of the coding pipeline.

Runs with no network and no API key. It validates everything except the two
steps that inherently need the outside world (collection and the model call),
and for the model call it asserts the request payload is well formed.

    python tests/test_pipeline.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "collect"))

import classify  # noqa: E402
import normalise  # noqa: E402
import describe  # noqa: E402
import reliability  # noqa: E402
from schema import CODEBOOK_VERSION, Coding, Stage, coding_json_schema  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(f"{name}: {detail}")
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    units_path = ROOT / "data" / "synthetic_pilot.jsonl"
    gold_path = ROOT / "data" / "synthetic_gold.jsonl"

    print("\n[1] schema and gold labels")
    units = classify.read_units(units_path)
    check("units parse", len(units) == 26, f"got {len(units)}")

    gold_rows = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("//")
    ]
    check("gold count matches units", len(gold_rows) == len(units))

    unit_ids = {u["unit_id"] for u in units}
    gold_ids = {g["unit_id"] for g in gold_rows}
    check("gold covers every unit", unit_ids == gold_ids, str(unit_ids ^ gold_ids))

    bad = []
    for row in gold_rows:
        try:
            Coding.model_validate(row["coding"])
        except Exception as exc:  # noqa: BLE001 - reporting, not handling
            bad.append(f"{row['unit_id']}: {exc}")
    check("every gold coding validates", not bad, "; ".join(bad[:3]))

    check(
        "gold uses the current codebook version",
        all(r["codebook_version"] == CODEBOOK_VERSION for r in gold_rows),
    )

    print("\n[2] taxonomy coverage")
    in_scope = [r for r in gold_rows if r["coding"]["in_scope"]]
    used = {r["coding"]["stage"] for r in in_scope}
    check(
        "every stage exercised by the fixture",
        used == {s.value for s in Stage},
        f"missing {sorted({s.value for s in Stage} - used)}",
    )
    check("fixture has out-of-scope units", len(in_scope) < len(gold_rows))

    print("\n[3] kappa arithmetic")
    check("identical coders give kappa 1", reliability.cohens_kappa("aabb", "aabb") == 1.0)
    perfect_disagreement = reliability.cohens_kappa(["a", "b"], ["b", "a"])
    check(
        "systematic disagreement gives kappa -1",
        abs(perfect_disagreement + 1.0) < 1e-9,
        str(perfect_disagreement),
    )
    # Worked 2x2: observed agreement .70, expected .52 -> kappa .375
    #   a marginals 60y/40n, b marginals 60y/40n
    #   pe = .6*.6 + .4*.4 = .52 ; k = (.70-.52)/(1-.52) = .375
    a = ["y"] * 45 + ["y"] * 15 + ["n"] * 15 + ["n"] * 25
    b = ["y"] * 45 + ["n"] * 15 + ["y"] * 15 + ["n"] * 25
    check(
        "worked 2x2 case gives kappa 0.375",
        abs(reliability.cohens_kappa(a, b) - 0.375) < 1e-9,
        f"{reliability.cohens_kappa(a, b):.4f}",
    )
    check(
        "both coders constant and identical is treated as agreement",
        reliability.cohens_kappa(["a", "a"], ["a", "a"]) == 1.0,
    )

    print("\n[4] reliability report on gold vs a perturbed coder")
    gold = reliability.load_codings(gold_path)
    perturbed = {k: dict(v) for k, v in gold.items()}
    for unit_id in ["syn-013", "syn-007", "syn-003"]:
        if unit_id in perturbed:
            perturbed[unit_id]["stage"] = "S3_SECONDARY"
    report = reliability.summarise(gold, perturbed)
    check("report covers stage", "stage" in report and report["stage"]["n"] > 0)
    check(
        "perturbation lowers kappa below 1",
        report["stage"]["kappa"] < 1.0,
        f"{report['stage']['kappa']:.3f}",
    )
    check(
        "identical coders pass the gate",
        reliability.summarise(gold, gold)["stage"]["passes"] is True,
    )

    print("\n[5] exhibits")
    with tempfile.TemporaryDirectory() as tmp:
        outdir = pathlib.Path(tmp)
        rows = describe.load(gold_path, units_path)
        check("describe drops out-of-scope units", len(rows) == len(in_scope))

        e1 = describe.e1_stage(rows)
        total_row = [r for r in e1 if r[0] == "TOTAL"][0]
        check("E1 total equals in-scope n", int(total_row[1]) == len(rows))
        shares = [float(r[2]) for r in e1[1:] if r[0] != "TOTAL"]
        check("E1 shares sum to 1", abs(sum(shares) - 1.0) < 1e-6, f"{sum(shares)}")

        e2 = describe.e2_attribution_by_stage(rows)
        check("E2 has a header and a total row", len(e2) >= 3 and e2[-1][0] == "TOTAL")

        check(
            "unit metadata joins onto coded rows",
            all(r.get("days_from_onsale") is not None for r in rows),
        )
        e3 = describe.e3_clock(rows)
        windows = [r for r in e3[1:] if r[0] != "unassigned"]
        check("E3 produces at least two time windows", len(windows) >= 2, str(len(windows)))
        unassigned = [r for r in e3 if r[0] == "unassigned"][0]
        check("E3 leaves nothing unassigned once joined", unassigned[-1] == "0", unassigned[-1])
        check(
            "E3 without a units file reports every row unassigned",
            describe.e3_clock(
                [{"coding": r["coding"]} for r in rows]
            )[-1][-1] == str(len(rows)),
        )

        e4 = describe.e4_money(rows)
        check("E4 picks up stated amounts", len(e4) >= 2, f"rows={len(e4)}")

        e6 = describe.e6_health(rows)
        diffuse = [r for r in e6 if r[0] == "diffuse_share"][0]
        check(
            "E6 diffuse gate evaluates",
            diffuse[3].startswith("PASS") or diffuse[3].startswith("FAIL"),
            diffuse[3],
        )

        describe.write_tsv(outdir / "E1.tsv", e1)
        check("exhibits write to disk", (outdir / "E1.tsv").exists())

    print("\n[6] request payload (built, not sent)")
    schema = coding_json_schema()
    check("schema forbids extra properties", schema["additionalProperties"] is False)
    check(
        "schema requires every field",
        set(schema["required"]) == set(schema["properties"]),
    )

    params = classify.build_params(units[0], classify.DEFAULT_MODEL, "medium")
    check("payload names the model", params["model"] == "claude-opus-5")
    check("payload uses adaptive thinking", params["thinking"] == {"type": "adaptive"})
    check(
        "payload carries the json_schema format",
        params["output_config"]["format"]["type"] == "json_schema",
    )
    check("payload sets effort", params["output_config"]["effort"] == "medium")
    check(
        "payload embeds the unit text",
        units[0]["text"] in params["messages"][0]["content"],
    )
    check("payload is JSON serialisable", bool(json.dumps(params, ensure_ascii=False)))

    system = classify.build_system(
        (ROOT / "codebook.md").read_text(encoding="utf-8")
    )
    check(
        "system prompt is marked cacheable",
        system[0]["cache_control"] == {"type": "ephemeral"},
    )
    check(
        "system prompt contains the codebook",
        "S1_ALLOCATION" in system[0]["text"] and "Cohen" not in system[0]["text"][:200],
    )

    print("\n[7] normalisation, hashing, event join")
    events = [{"key": "e1", "onsale_date": "2026-03-02", "keywords": ["紅館"]}]
    timed = [dict(events[0], onsale_time="10:00")]
    raw = {
        "id": "42",
        "author_id": "userA",
        "posted_at": "2026-03-04T09:30:00+08:00",
        "text": "紅館個場黃牛叫價 $8000",
    }
    unit = normalise.normalise(raw, "syn", salt="pilot-salt", events=events)
    check("keyword join finds the event", unit["event_key"] == "e1")
    check(
        "midnight anchor measures from the start of the on-sale day",
        abs(unit["days_from_onsale"] - 2.396) < 0.01,
        str(unit["days_from_onsale"]),
    )
    timed_unit = normalise.normalise(raw, "syn", salt="pilot-salt", events=timed)
    check(
        "an explicit on-sale time shifts the anchor",
        abs(timed_unit["days_from_onsale"] - 1.979) < 0.01,
        str(timed_unit["days_from_onsale"]),
    )
    early = normalise.normalise(
        dict(raw, id="43", posted_at="2026-03-02T09:30:00+08:00"),
        "syn",
        salt="pilot-salt",
        events=timed,
    )
    check("a pre-sale post is negative", early["days_from_onsale"] < 0)
    check(
        "unmatched text is left unassigned",
        normalise.normalise(
            dict(raw, id="44", text="冇關鍵字"), "syn", salt="s", events=events
        )["event_key"]
        is None,
    )

    check("author_key is not the raw handle", unit["author_key"] != "userA")
    check(
        "different salts give different keys",
        normalise.author_key("s", "userA", "salt1")
        != normalise.author_key("s", "userA", "salt2"),
    )
    unsalted_rejected = False
    try:
        normalise.author_key("s", "userA", "")
    except ValueError:
        unsalted_rejected = True
    check("unsalted hashing is refused", unsalted_rejected)

    check(
        "duplicate inside the window is dropped",
        len(normalise.dedupe([dict(unit), dict(unit, posted_at="2026-03-04T15:30:00+08:00")]))
        == 1,
    )
    check(
        "repeat outside the window is kept",
        len(normalise.dedupe([dict(unit), dict(unit, posted_at="2026-03-06T15:30:00+08:00")]))
        == 2,
    )

    template_rejected = False
    try:
        normalise.load_events(ROOT / "data" / "events.template.json")
    except ValueError:
        template_rejected = True
    check("event template with null dates is refused", template_rejected)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for failure in FAILED:
        print(f"  - {failure}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
