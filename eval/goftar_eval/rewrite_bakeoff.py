"""Compare AI models for Clean, Professional and Translate (decision D5).

Usage (from the eval/ directory):
  python -m goftar_eval.rewrite_bakeoff \
      --model anthropic:claude-haiku-5-5@low --model anthropic:claude-sonnet-5-5@low \
      --out results/rewrite1

Model specs:
  anthropic:<model-id>[@effort]   Claude API (needs ANTHROPIC_API_KEY); effort low|medium|high
  file:<outputs.jsonl>            precomputed {"id", "text"} lines from any other model

Writes:
  summary.md / summary.csv   automatic faithfulness checks per model and task
  <model>.jsonl              every output with its check results
  rating_sheet.csv           blind sheet for human rating (models hidden as A, B, ...)
  rating_key.json            which letter is which model (open only after rating)
"""

import argparse
import csv
import json
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

from .bakeoff import EVAL_DIR, load_jsonl, to_markdown
from .faithfulness import check
from .prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_message


class FileModel:
    def __init__(self, path: str):
        self.name = f"file:{Path(path).stem}"
        self._rows = {r["id"]: r for r in load_jsonl(Path(path))}

    def generate(self, case):
        row = self._rows[case["id"]]
        return row["text"], row.get("latency_ms"), None


class AnthropicModel:
    def __init__(self, model: str, effort: str | None = None):
        import anthropic  # optional dependency

        self.name = f"anthropic:{model}" + (f"@{effort}" if effort else "")
        self._model = model
        self._effort = effort
        self._client = anthropic.Anthropic()

    def generate(self, case):
        kwargs = {}
        if self._effort:
            kwargs["output_config"] = {"effort": self._effort}
        start = time.perf_counter()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4000,
            # Cached once the prompt grows past the model's minimum cacheable length.
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": build_user_message(case)}],
            **kwargs,
        )
        latency = (time.perf_counter() - start) * 1000
        if response.stop_reason == "refusal":
            return "", latency, "refusal"
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        error = "max_tokens" if response.stop_reason == "max_tokens" else None
        return text, latency, error


def build_model(spec: str):
    kind, _, arg = spec.partition(":")
    if kind == "file":
        return FileModel(arg)
    if kind == "anthropic":
        model, _, effort = arg.partition("@")
        return AnthropicModel(model, effort or None)
    raise ValueError(f"unknown model provider '{kind}'")


def evaluate(case: dict, output: str, latency, error) -> dict:
    result = check(case["input"], output, task=case["task"], output_lang=case["output_lang"],
                   keep_terms=case.get("keep_terms", []),
                   allow_dropped_numbers=case.get("allow_dropped_numbers", []))
    return {
        "id": case["id"], "task": case["task"], "output_lang": case["output_lang"],
        "input": case["input"], "output": output, "error": error,
        "passed": result.passed and not error, "failures": result.failures(),
        "numbers_missing": result.numbers_missing, "numbers_added": result.numbers_added,
        "terms_missing": result.terms_missing, "latency_ms": latency,
    }


CHECKS = ("numbers_missing", "numbers_added", "terms_missing", "negation_mismatch",
          "wrong_language", "too_long", "empty")


def summarise(rows):
    lat = sorted(r["latency_ms"] for r in rows if r["latency_ms"] is not None)
    out = {"n": len(rows), "pass %": round(100 * sum(r["passed"] for r in rows) / len(rows), 1)}
    for c in CHECKS:
        out[c] = sum(c in r["failures"] for r in rows)
    out["errors"] = sum(bool(r["error"]) for r in rows)
    out["latency p50 ms"] = round(statistics.median(lat)) if lat else None
    out["latency p95 ms"] = round(lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))]) if lat else None
    return out


def write_rating_sheet(results: dict, out_dir: Path, seed: int = 7):
    rng = random.Random(seed)
    names = list(results)
    letters = [chr(ord("A") + i) for i in range(len(names))]
    rng.shuffle(letters)
    key = dict(zip(letters, names))
    rows = []
    for letter, name in key.items():
        for r in results[name]:
            rows.append({"case": r["id"], "system": letter, "task": r["task"], "input": r["input"],
                         "output": r["output"], "meaning_1to5": "", "fluency_1to5": "",
                         "tone_1to5": "", "critical_error_yes_no": "", "comment": ""})
    rng.shuffle(rows)
    rows.sort(key=lambda r: r["case"])  # group by case, systems in random order
    with open(out_dir / "rating_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "rating_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")


def run(cases, models, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for model in models:
        rows = []
        for case in cases:
            try:
                text, latency, error = model.generate(case)
            except Exception as exc:  # keep going; record the failure
                text, latency, error = "", None, f"{type(exc).__name__}: {exc}"
            rows.append(evaluate(case, text, latency, error))
        results[model.name] = rows
        safe = model.name.replace(":", "_").replace("/", "_").replace("@", "_")
        with open(out_dir / f"{safe}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    table = []
    for name, rows in results.items():
        table.append({"model": name, "group": "ALL", **summarise(rows)})
        by_task = defaultdict(list)
        for r in rows:
            by_task[r["task"]].append(r)
        for task in sorted(by_task):
            table.append({"model": name, "group": f"task={task}", **summarise(by_task[task])})
    header = f"Prompt version: {PROMPT_VERSION}\n\n"
    (out_dir / "summary.md").write_text(header + to_markdown(table), encoding="utf-8")
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    write_rating_sheet(results, out_dir)
    return table, results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, default=EVAL_DIR / "corpus/llm_cases.jsonl")
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--out", type=Path, default=Path("results/rewrite"))
    args = ap.parse_args(argv)
    table, _ = run(load_jsonl(args.cases), [build_model(m) for m in args.model], args.out)
    print(to_markdown(table))


if __name__ == "__main__":
    main()
