"""Inter-coder reliability for the ticketing-discontent pilot.

Cohen's kappa, implemented directly rather than pulled from scikit-learn, so the
go/no-go gate has no heavy dependency and the arithmetic is auditable.

Usage:
    python src/reliability.py --a coded_human_A.jsonl --b coded_human_B.jsonl
    python src/reliability.py --a gold.jsonl --b coded_model.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from schema import RELIABILITY_THRESHOLDS  # noqa: E402


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Cohen's kappa for two coders over the same units.

    Returns 1.0 when both coders are constant and identical: they agree
    perfectly and there is no disagreement to discount. Chance-corrected
    agreement is undefined there in the usual sense, so this is a convention,
    and it is flagged by the `degenerate` field in summarise().
    """
    if len(a) != len(b):
        raise ValueError("coders must cover the same units")
    n = len(a)
    if n == 0:
        raise ValueError("no overlapping units")

    observed = sum(1 for x, y in zip(a, b) if x == y) / n

    count_a, count_b = Counter(a), Counter(b)
    expected = sum(
        (count_a[label] / n) * (count_b[label] / n)
        for label in set(count_a) | set(count_b)
    )

    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)


def load_codings(path: pathlib.Path) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        row = json.loads(line)
        if "error" in row:
            continue
        out[row["unit_id"]] = row["coding"]
    return out


def aligned(
    a: Dict[str, dict], b: Dict[str, dict], field: str
) -> Tuple[List[str], List[str], List[str]]:
    """Values for units both coders coded and both judged in scope."""
    unit_ids = sorted(set(a) & set(b))
    keep, va, vb = [], [], []
    for unit_id in unit_ids:
        ca, cb = a[unit_id], b[unit_id]
        if not (ca.get("in_scope", True) and cb.get("in_scope", True)):
            continue
        keep.append(unit_id)
        va.append(str(ca.get(field)))
        vb.append(str(cb.get(field)))
    return keep, va, vb


def summarise(
    a: Dict[str, dict], b: Dict[str, dict], fields: Optional[Sequence[str]] = None
) -> Dict[str, dict]:
    fields = list(fields or RELIABILITY_THRESHOLDS)
    report: Dict[str, dict] = {}

    scope_ids = sorted(set(a) & set(b))
    if scope_ids:
        report["in_scope"] = {
            "n": len(scope_ids),
            "kappa": cohens_kappa(
                [str(a[i].get("in_scope", True)) for i in scope_ids],
                [str(b[i].get("in_scope", True)) for i in scope_ids],
            ),
            "threshold": None,
            "passes": None,
            "degenerate": False,
        }

    for field in fields:
        unit_ids, va, vb = aligned(a, b, field)
        if not unit_ids:
            report[field] = {"n": 0, "kappa": None, "passes": False}
            continue
        kappa = cohens_kappa(va, vb)
        threshold = RELIABILITY_THRESHOLDS.get(field)
        report[field] = {
            "n": len(unit_ids),
            "kappa": kappa,
            "observed_agreement": sum(1 for x, y in zip(va, vb) if x == y) / len(va),
            "threshold": threshold,
            "passes": None if threshold is None else kappa >= threshold,
            "degenerate": len(set(va)) == 1 and len(set(vb)) == 1,
        }
    return report


def confusion(a: Dict[str, dict], b: Dict[str, dict], field: str) -> Counter:
    _, va, vb = aligned(a, b, field)
    return Counter(zip(va, vb))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=pathlib.Path, required=True)
    parser.add_argument("--b", type=pathlib.Path, required=True)
    parser.add_argument("--confusion", metavar="FIELD")
    args = parser.parse_args()

    coder_a, coder_b = load_codings(args.a), load_codings(args.b)
    report = summarise(coder_a, coder_b)

    print(f"{'field':<20}{'n':>6}{'kappa':>9}{'thresh':>9}  verdict")
    for field, stats in report.items():
        kappa = stats["kappa"]
        kappa_text = "n/a" if kappa is None else f"{kappa:.3f}"
        threshold = stats.get("threshold")
        thresh_text = "-" if threshold is None else f"{threshold:.2f}"
        if stats.get("passes") is None:
            verdict = "-"
        else:
            verdict = "PASS" if stats["passes"] else "FAIL"
        if stats.get("degenerate"):
            verdict += " (degenerate: no label variation)"
        print(f"{field:<20}{stats['n']:>6}{kappa_text:>9}{thresh_text:>9}  {verdict}")

    if args.confusion:
        print(f"\nconfusion for {args.confusion} (a -> b):")
        for (x, y), count in confusion(coder_a, coder_b, args.confusion).most_common():
            if x != y:
                print(f"  {x:<18} -> {y:<18} {count}")

    gates = [s["passes"] for s in report.values() if s.get("passes") is not None]
    if gates and not all(gates):
        print("\nGATE FAILED: reconcile and revise the codebook before scaling up.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
