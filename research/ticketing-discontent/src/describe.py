"""Build the pilot exhibits from coded units.

Pure standard library, writing TSV, so an RA can open the output in Excel and a
referee can recompute it without installing anything.

Exhibits:
  E1  stage composition            - the headline decomposition
  E2  attribution x stage          - who gets blamed for what
  E3  grievance clock              - stage composition by days from on-sale
  E4  stated money amounts         - by stage, from money_claim_hkd
  E5  stance composition           - grievance / resignation / mobilisation / defence
  E6  taxonomy health              - diffuse share and first-person share

E6 is a gate, not a result: a diffuse share above 0.20 means the taxonomy is not
partitioning the corpus and needs revision before any of E1-E5 is reported.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

DIFFUSE_GATE = 0.20


# Metadata carried from the units file onto coded rows. Coded records hold
# only the coding; the time and source fields that E3 needs live with the unit,
# so the two must be joined before the exhibits are built.
JOIN_FIELDS = ("days_from_onsale", "posted_at", "source", "thread_title")


def _read_jsonl(path: pathlib.Path) -> List[Dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            rows.append(json.loads(line))
    return rows


def load(
    path: pathlib.Path, units_path: Optional[pathlib.Path] = None
) -> List[Dict[str, Any]]:
    """Load coded units, optionally joining unit metadata by unit_id.

    Without `units_path` the time-based exhibit (E3) has nothing to bin on and
    reports every row as unassigned, so pass it whenever E3 matters.
    """
    units: Dict[str, Dict[str, Any]] = {}
    if units_path is not None:
        units = {u["unit_id"]: u for u in _read_jsonl(units_path)}

    rows = []
    for row in _read_jsonl(path):
        if "error" in row:
            continue
        if not row["coding"].get("in_scope", True):
            continue
        unit = units.get(row["unit_id"], {})
        for field in JOIN_FIELDS:
            if field in unit and row.get(field) is None:
                row[field] = unit[field]
        rows.append(row)
    return rows


def _share_table(counts: Counter, total: int) -> List[List[str]]:
    table = [["value", "n", "share"]]
    for value, count in counts.most_common():
        table.append([value, str(count), f"{count / total:.4f}"])
    table.append(["TOTAL", str(total), "1.0000"])
    return table


def e1_stage(rows: List[Dict[str, Any]]) -> List[List[str]]:
    counts = Counter(r["coding"]["stage"] for r in rows)
    return _share_table(counts, len(rows))


def e2_attribution_by_stage(rows: List[Dict[str, Any]]) -> List[List[str]]:
    stages = sorted({r["coding"]["stage"] for r in rows})
    attributions = sorted({r["coding"]["attribution"] for r in rows})
    cell: Dict[tuple, int] = defaultdict(int)
    for row in rows:
        cell[(row["coding"]["attribution"], row["coding"]["stage"])] += 1

    table = [["attribution", *stages, "TOTAL"]]
    for attribution in attributions:
        counts = [cell[(attribution, stage)] for stage in stages]
        table.append([attribution, *[str(c) for c in counts], str(sum(counts))])
    totals = [sum(cell[(a, s)] for a in attributions) for s in stages]
    table.append(["TOTAL", *[str(t) for t in totals], str(sum(totals))])
    return table


def e3_clock(rows: List[Dict[str, Any]], bins: Optional[List[int]] = None):
    """Stage composition by days from on-sale.

    Requires `days_from_onsale` on each row, joined in during collection from
    the event calendar. Rows without it are reported as unassigned.
    """
    bins = bins or [-7, -1, 0, 1, 3, 7, 30]

    def bucket(days: float) -> str:
        if days < bins[0]:
            return f"<{bins[0]}"
        for low, high in zip(bins, bins[1:]):
            if low <= days < high:
                return f"[{low},{high})"
        return f">={bins[-1]}"

    stages = sorted({r["coding"]["stage"] for r in rows})
    cell: Dict[tuple, int] = defaultdict(int)
    unassigned = 0
    for row in rows:
        days = row.get("days_from_onsale")
        if days is None:
            unassigned += 1
            continue
        cell[(bucket(days), row["coding"]["stage"])] += 1

    order = [f"<{bins[0]}"] + [
        f"[{low},{high})" for low, high in zip(bins, bins[1:])
    ] + [f">={bins[-1]}"]
    table = [["window_days", *stages, "n"]]
    for window in order:
        counts = [cell[(window, stage)] for stage in stages]
        total = sum(counts)
        if total == 0:
            continue
        shares = [f"{c / total:.3f}" for c in counts]
        table.append([window, *shares, str(total)])
    table.append(["unassigned", *["" for _ in stages], str(unassigned)])
    return table


def e4_money(rows: List[Dict[str, Any]]) -> List[List[str]]:
    by_stage: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        amount = row["coding"].get("money_claim_hkd")
        if amount is not None:
            by_stage[row["coding"]["stage"]].append(float(amount))

    table = [["stage", "n_with_amount", "median_hkd", "p25", "p75", "max"]]
    for stage in sorted(by_stage):
        values = sorted(by_stage[stage])
        quantiles = (
            statistics.quantiles(values, n=4) if len(values) >= 4 else [None, None, None]
        )
        table.append(
            [
                stage,
                str(len(values)),
                f"{statistics.median(values):.0f}",
                "" if quantiles[0] is None else f"{quantiles[0]:.0f}",
                "" if quantiles[2] is None else f"{quantiles[2]:.0f}",
                f"{max(values):.0f}",
            ]
        )
    return table


def e5_stance(rows: List[Dict[str, Any]]) -> List[List[str]]:
    counts = Counter(r["coding"]["affect"] for r in rows)
    return _share_table(counts, len(rows))


def e6_health(rows: List[Dict[str, Any]]) -> List[List[str]]:
    total = len(rows)
    diffuse = sum(1 for r in rows if r["coding"]["stage"] == "S0_DIFFUSE")
    first_person = sum(1 for r in rows if r["coding"].get("first_person"))
    remedy = sum(1 for r in rows if r["coding"].get("remedy_named"))
    diffuse_share = diffuse / total if total else 0.0
    return [
        ["metric", "value", "gate", "verdict"],
        [
            "diffuse_share",
            f"{diffuse_share:.4f}",
            f"<{DIFFUSE_GATE}",
            "PASS" if diffuse_share < DIFFUSE_GATE else "FAIL: revise taxonomy",
        ],
        ["first_person_share", f"{first_person / total:.4f}" if total else "0", "-", "-"],
        ["remedy_named_share", f"{remedy / total:.4f}" if total else "0", "-", "-"],
        ["n_in_scope", str(total), "-", "-"],
    ]


def write_tsv(path: pathlib.Path, table: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join("\t".join(str(c) for c in row) for row in table) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coded", type=pathlib.Path, required=True)
    parser.add_argument(
        "--units",
        type=pathlib.Path,
        help="Units file to join metadata from. Required for E3.",
    )
    parser.add_argument("--outdir", type=pathlib.Path, required=True)
    args = parser.parse_args()

    rows = load(args.coded, args.units)
    if args.units is None:
        print("note: --units not given, E3 (grievance clock) will be unassigned")
    if not rows:
        raise SystemExit("no in-scope coded units")

    exhibits = {
        "E1_stage_composition": e1_stage(rows),
        "E2_attribution_by_stage": e2_attribution_by_stage(rows),
        "E3_grievance_clock": e3_clock(rows),
        "E4_money_claims": e4_money(rows),
        "E5_stance": e5_stance(rows),
        "E6_taxonomy_health": e6_health(rows),
    }
    for name, table in exhibits.items():
        write_tsv(args.outdir / f"{name}.tsv", table)
        print(f"\n== {name} ==")
        for row in table:
            print("  " + "\t".join(str(c) for c in row))

    print(f"\nwrote {len(exhibits)} exhibits to {args.outdir}")


if __name__ == "__main__":
    main()
