"""LLM coding harness for the ticketing-discontent corpus.

Two modes:
  sync   - one request per unit, concurrent. Use for the pilot (n <= ~1000).
  batch  - Message Batches API at 50% cost. Use for the full corpus.

Both share one request builder, so the payload the pilot validates is the
payload the full run sends. `--dry-run` prints that payload and makes no
network call, which is how the pipeline is checked in an offline environment.

The codebook is sent as a cached system prompt: it is identical across every
unit, so it should be paid for once per cache window rather than per unit.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List

from pydantic import ValidationError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from schema import CODEBOOK_VERSION, Coding, coding_json_schema  # noqa: E402

DEFAULT_MODEL = "claude-opus-5"
CODEBOOK_PATH = pathlib.Path(__file__).resolve().parent.parent / "codebook.md"

INSTRUCTIONS = """You are coding social media posts for an academic study of \
public discontent with event ticketing in Hong Kong.

Apply the codebook below exactly. It is the only authority; do not import \
intuitions from other coding schemes.

The corpus is majority written Cantonese with heavy code-mixing and \
traditional characters. Read it as a Hong Kong reader would. Sarcasm and \
negation routinely invert surface sentiment, so judge the author's stance, not \
the polarity of individual words.

Two rules coders get wrong most often:
- `attribution` is NONE unless blame is explicit. Naming an operator is not \
blaming it.
- `stage` is where the grievance ORIGINATES, not what the author mentions \
last. A complaint about paying a scalper's markup because the public sale was \
90% internal tickets originates at S1_ALLOCATION.

Return only the structured object. The `rationale` must quote the phrase that \
decided the stage.

--- CODEBOOK ---
{codebook}
--- END CODEBOOK ---"""


def build_system(codebook_text: str) -> List[Dict[str, Any]]:
    """System prompt as a single cacheable block."""
    return [
        {
            "type": "text",
            "text": INSTRUCTIONS.format(codebook=codebook_text),
            "cache_control": {"type": "ephemeral"},
        }
    ]


def build_params(unit: Dict[str, Any], model: str, effort: str) -> Dict[str, Any]:
    """Message params for one unit. Shared by sync and batch paths."""
    context_bits = []
    if unit.get("posted_at"):
        context_bits.append(f"posted_at: {unit['posted_at']}")
    if unit.get("source"):
        context_bits.append(f"source: {unit['source']}")
    if unit.get("thread_title"):
        context_bits.append(f"thread_title: {unit['thread_title']}")
    context = "\n".join(context_bits)

    return {
        "model": model,
        "max_tokens": 4000,
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": effort,
            "format": {"type": "json_schema", "schema": coding_json_schema()},
        },
        "messages": [
            {
                "role": "user",
                "content": f"{context}\n\n--- UNIT TEXT ---\n{unit['text']}",
            }
        ],
    }


def parse_response_text(text: str) -> Coding:
    return Coding.model_validate(json.loads(text))


def code_sync(
    units: List[Dict[str, Any]], model: str, effort: str, workers: int
) -> List[Dict[str, Any]]:
    import anthropic

    client = anthropic.Anthropic()
    system = build_system(CODEBOOK_PATH.read_text(encoding="utf-8"))

    def one(unit: Dict[str, Any]) -> Dict[str, Any]:
        params = build_params(unit, model, effort)
        try:
            response = client.messages.create(system=system, **params)
        except anthropic.APIStatusError as exc:
            return {"unit_id": unit["unit_id"], "error": f"{exc.status_code}: {exc}"}
        except anthropic.APIConnectionError as exc:
            return {"unit_id": unit["unit_id"], "error": f"connection: {exc}"}

        if response.stop_reason == "refusal":
            return {"unit_id": unit["unit_id"], "error": "refusal"}

        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            coding = parse_response_text(text)
        except (ValidationError, json.JSONDecodeError) as exc:
            return {"unit_id": unit["unit_id"], "error": f"parse: {exc}"}

        return {
            "unit_id": unit["unit_id"],
            "source": unit.get("source", ""),
            "coder": f"model:{model}",
            "codebook_version": CODEBOOK_VERSION,
            "coding": coding.model_dump(mode="json"),
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_input_tokens": getattr(
                    response.usage, "cache_read_input_tokens", 0
                ),
            },
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, units))


def code_batch(units: List[Dict[str, Any]], model: str, effort: str) -> str:
    """Submit a batch and return its id. Results are fetched by --fetch-batch."""
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = anthropic.Anthropic()
    system = build_system(CODEBOOK_PATH.read_text(encoding="utf-8"))

    requests = [
        Request(
            custom_id=unit["unit_id"],
            params=MessageCreateParamsNonStreaming(
                system=system, **build_params(unit, model, effort)
            ),
        )
        for unit in units
    ]
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def fetch_batch(batch_id: str, model: str) -> List[Dict[str, Any]]:
    import anthropic

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        raise SystemExit(f"batch {batch_id} is {batch.processing_status}, not ended")

    out: List[Dict[str, Any]] = []
    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            out.append({"unit_id": result.custom_id, "error": result.result.type})
            continue
        message = result.result.message
        text = next((b.text for b in message.content if b.type == "text"), "")
        try:
            coding = parse_response_text(text)
        except (ValidationError, json.JSONDecodeError) as exc:
            out.append({"unit_id": result.custom_id, "error": f"parse: {exc}"})
            continue
        out.append(
            {
                "unit_id": result.custom_id,
                "coder": f"model:{model}",
                "codebook_version": CODEBOOK_VERSION,
                "coding": coding.model_dump(mode="json"),
            }
        )
    return out


def read_units(path: pathlib.Path) -> List[Dict[str, Any]]:
    units = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            units.append(json.loads(line))
    return units


def write_jsonl(path: pathlib.Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--effort",
        default="medium",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Sweep low/medium against the gold set before settling.",
    )
    parser.add_argument("--mode", default="sync", choices=["sync", "batch"])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--fetch-batch", metavar="BATCH_ID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request payload for the first unit and exit. No network.",
    )
    args = parser.parse_args()

    if args.fetch_batch:
        rows = fetch_batch(args.fetch_batch, args.model)
        write_jsonl(args.output, rows)
        print(f"wrote {len(rows)} rows to {args.output}")
        return

    units = read_units(args.input)
    if not units:
        raise SystemExit(f"no units in {args.input}")

    if args.dry_run:
        codebook = (
            CODEBOOK_PATH.read_text(encoding="utf-8")
            if CODEBOOK_PATH.exists()
            else "<codebook.md missing>"
        )
        system = build_system(codebook)
        params = build_params(units[0], args.model, args.effort)
        print(f"units: {len(units)}")
        print(f"system prompt chars: {len(system[0]['text'])} (cached)")
        print(json.dumps(params, ensure_ascii=False, indent=2)[:4000])
        return

    if args.mode == "batch":
        batch_id = code_batch(units, args.model, args.effort)
        print(f"submitted batch {batch_id} ({len(units)} units)")
        print(f"fetch with: --fetch-batch {batch_id} --output <path>")
        return

    rows = code_sync(units, args.model, args.effort, args.workers)
    write_jsonl(args.output, rows)
    errors = sum(1 for r in rows if "error" in r)
    print(f"wrote {len(rows)} rows to {args.output} ({errors} errors)")


if __name__ == "__main__":
    main()
