"""Run the speech recognition comparison and write a report.

Usage (from the eval/ directory):
  python -m goftar_eval.bakeoff --manifest recordings/manifest.jsonl \
      --provider faster-whisper:large-v3-turbo --provider openai:whisper-1 --bias

Manifest lines (JSONL, audio paths relative to the manifest file):
  {"id": "r001", "audio": "spk01/fa01.wav", "prompt_id": "fa01",
   "speaker": "spk01", "accent": "tehrani", "condition": "clean"}
Free-speech recordings give their own text instead of prompt_id:
  {"id": "r900", "audio": "...", "reference": "...", "category": "mixed", "terms": [...]}
"""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .metrics import char_errors, number_diff, term_retention, word_errors
from .normalize import script_profile
from .providers import Recording, build_provider

EVAL_DIR = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_recordings(manifest: Path, prompts: Path) -> list[Recording]:
    by_id = {p["id"]: p for p in load_jsonl(prompts)}
    recs = []
    for row in load_jsonl(manifest):
        prompt = by_id.get(row.get("prompt_id"), {})
        if not prompt and "reference" not in row:
            raise ValueError(f"{row['id']}: unknown prompt_id and no reference text")
        audio = row.get("audio")
        recs.append(Recording(
            id=row["id"],
            audio=(manifest.parent / audio) if audio else None,
            reference=row.get("reference", prompt.get("text", "")),
            category=row.get("category", prompt.get("category", "unknown")),
            terms=row.get("terms", prompt.get("terms", [])),
            speaker=row.get("speaker", ""),
            accent=row.get("accent", ""),
            condition=row.get("condition", "clean"),
        ))
    return recs


def score(rec: Recording, hyp: str, latency_ms) -> dict:
    w, c = word_errors(rec.reference, hyp), char_errors(rec.reference, hyp)
    kept, total = term_retention(rec.terms, hyp)
    nums = number_diff(rec.reference, hyp)
    return {
        "id": rec.id, "category": rec.category, "accent": rec.accent,
        "condition": rec.condition, "speaker": rec.speaker,
        "reference": rec.reference, "hypothesis": hyp,
        "word_errors": w.errors, "ref_words": w.ref_len,
        "char_errors": c.errors, "ref_chars": c.ref_len,
        "terms_kept": kept, "terms_total": total,
        "numbers_missing": nums.missing, "numbers_added": nums.added,
        "numbers_total": nums.ref_count,
        "lang_label_ok": script_profile(hyp) == rec.category,
        "latency_ms": latency_ms,
    }


def _pct(n, d):
    return round(100 * n / d, 1) if d else None


def summarise(rows: list[dict]) -> dict:
    lat = sorted(r["latency_ms"] for r in rows if r["latency_ms"] is not None)
    p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))] if lat else None
    num_total = sum(r["numbers_total"] for r in rows)
    return {
        "n": len(rows),
        "WER %": _pct(sum(r["word_errors"] for r in rows), sum(r["ref_words"] for r in rows)),
        "CER %": _pct(sum(r["char_errors"] for r in rows), sum(r["ref_chars"] for r in rows)),
        "terms kept %": _pct(sum(r["terms_kept"] for r in rows), sum(r["terms_total"] for r in rows)),
        "numbers kept %": _pct(num_total - sum(len(r["numbers_missing"]) for r in rows), num_total),
        "lang label %": _pct(sum(r["lang_label_ok"] for r in rows), len(rows)),
        "latency p50 ms": round(statistics.median(lat)) if lat else None,
        "latency p95 ms": round(p95) if p95 is not None else None,
    }


GROUPINGS = ("category", "condition", "accent")


def build_summary(results: dict[str, list[dict]]) -> list[dict]:
    table = []
    for provider, rows in results.items():
        table.append({"provider": provider, "group": "ALL", **summarise(rows)})
        for key in GROUPINGS:
            groups = defaultdict(list)
            for r in rows:
                if r[key]:
                    groups[r[key]].append(r)
            for value in sorted(groups):
                table.append({"provider": provider, "group": f"{key}={value}", **summarise(groups[value])})
    return table


def to_markdown(table: list[dict]) -> str:
    if not table:
        return "No results.\n"
    cols = list(table[0])
    fmt = lambda v: "–" if v is None else str(v)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(fmt(r[c]) for c in cols) + " |" for r in table]
    return "\n".join(lines) + "\n"


def run(recordings, providers, prompt, out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for provider in providers:
        rows = []
        for rec in recordings:
            try:
                t = provider.transcribe(rec, prompt)
                rows.append(score(rec, t.text, t.latency_ms))
            except Exception as exc:  # keep going; report the failure
                print(f"[{provider.name}] {rec.id}: {exc}")
        results[provider.name] = rows
        safe = provider.name.replace(":", "_").replace("/", "_")
        with open(out_dir / f"{safe}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    table = build_summary(results)
    (out_dir / "summary.md").write_text(to_markdown(table), encoding="utf-8")
    if table:
        with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    return table


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--prompts", type=Path, default=EVAL_DIR / "corpus/prompts.jsonl")
    ap.add_argument("--glossary", type=Path, default=EVAL_DIR / "corpus/glossary.json")
    ap.add_argument("--provider", action="append", required=True)
    ap.add_argument("--bias", action="store_true", help="send glossary terms as the decoder prompt")
    ap.add_argument("--out", type=Path, default=Path("results"))
    args = ap.parse_args(argv)

    recordings = load_recordings(args.manifest, args.prompts)
    prompt = None
    if args.bias:
        terms = json.loads(args.glossary.read_text(encoding="utf-8"))["terms"]
        prompt = "Persian and English. Terms: " + ", ".join(terms) + "."
    providers = [build_provider(p) for p in args.provider]
    table = run(recordings, providers, prompt, args.out)
    print(to_markdown(table))


if __name__ == "__main__":
    main()
