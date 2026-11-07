import json
import tempfile
import unittest
from pathlib import Path

from goftar_eval.bakeoff import load_recordings, run
from goftar_eval.metrics import char_errors, number_diff, term_retention, word_errors
from goftar_eval.normalize import normalize_for_scoring, script_profile
from goftar_eval.providers import FileProvider

EVAL_DIR = Path(__file__).resolve().parent.parent
PROMPTS = EVAL_DIR / "corpus/prompts.jsonl"


class NormalizeTests(unittest.TestCase):
    def test_arabic_letter_forms_match_persian(self):
        self.assertEqual(normalize_for_scoring("كيف"), normalize_for_scoring("کیف"))

    def test_digits_and_thousands(self):
        self.assertEqual(normalize_for_scoring("۴۵٬۰۰۰ دلار"), "45000 دلار")
        self.assertEqual(normalize_for_scoring("$45,000"), "45000")

    def test_zwnj_and_mi_prefix_variants_match(self):
        a = normalize_for_scoring("می‌خواهم")
        self.assertEqual(a, normalize_for_scoring("میخواهم"))
        self.assertEqual(a, normalize_for_scoring("می خواهم"))

    def test_punctuation_case_and_bidi_marks_ignored(self):
        self.assertEqual(
            normalize_for_scoring("«لطفاً⁨ Scope⁩ of Work»، کن."),
            normalize_for_scoring("لطفا scope of work کن"),
        )

    def test_script_profile(self):
        self.assertEqual(script_profile("سلام، حالت چطوره؟"), "fa")
        self.assertEqual(script_profile("Hello there"), "en")
        self.assertEqual(script_profile("لطفاً این Scope of Work رو آماده کن"), "mixed")
        self.assertEqual(script_profile("123"), "unknown")


class MetricTests(unittest.TestCase):
    def test_wer(self):
        self.assertEqual(word_errors("a b c d", "a b c d").errors, 0)
        e = word_errors("the quick brown fox", "the quick fox jumps")
        self.assertEqual((e.errors, e.ref_len), (2, 4))

    def test_cer_ignores_spaces(self):
        self.assertEqual(char_errors("ab cd", "abcd").errors, 0)

    def test_term_retention_detects_transliteration(self):
        terms = ["Scope of Work", "Contractor"]
        self.assertEqual(term_retention(terms, "این Scope of Work رو برای Contractor"), (2, 2))
        self.assertEqual(term_retention(terms, "این اسکوپ آف ورک رو برای Contractor"), (1, 2))
        # Partial-word matches don't count.
        self.assertEqual(term_retention(["RFI"], "RFIs"), (0, 1))

    def test_number_diff(self):
        d = number_diff("Variation ۱۲ costs $45,000", "Variation 12 costs $54,000")
        self.assertEqual((d.missing, d.added, d.ref_count), (["45000"], ["54000"], 2))
        self.assertEqual(d.recall, 0.5)
        self.assertEqual(number_diff("no numbers", "none").recall, 1.0)


class CorpusTests(unittest.TestCase):
    def test_prompts_are_valid(self):
        rows = [json.loads(l) for l in PROMPTS.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        for r in rows:
            self.assertEqual(script_profile(r["text"]), r["category"], r["id"])
            kept, total = term_retention(r["terms"], r["text"])
            self.assertEqual(kept, total, f"{r['id']}: term not in its own text")


class BakeoffTests(unittest.TestCase):
    def test_end_to_end_with_file_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest = tmp / "manifest.jsonl"
            manifest.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
                {"id": "r1", "prompt_id": "mx01", "speaker": "s1", "accent": "tehrani"},
                {"id": "r2", "prompt_id": "en05", "speaker": "s2", "accent": "au", "condition": "noisy"},
                {"id": "r3", "reference": "سلام دنیا", "category": "fa", "terms": []},
            ]), encoding="utf-8")
            hyps = tmp / "vendor.jsonl"
            hyps.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
                {"id": "r1", "text": "لطفا این اسکوپ آف ورک رو برای Contractor آماده کن", "latency_ms": 900},
                {"id": "r2", "text": "The quote came in at $45,000 plus GST.", "latency_ms": 700},
                {"id": "r3", "text": "سلام دنیا", "latency_ms": 500},
            ]), encoding="utf-8")

            recs = load_recordings(manifest, PROMPTS)
            table = run(recs, [FileProvider(str(hyps))], None, tmp / "out")

            overall = table[0]
            self.assertEqual(overall["group"], "ALL")
            self.assertEqual(overall["n"], 3)
            self.assertEqual(overall["terms kept %"], 66.7)  # Scope of Work lost, Contractor + GST kept
            self.assertEqual(overall["numbers kept %"], 100.0)
            self.assertEqual(overall["latency p50 ms"], 700)
            groups = {r["group"] for r in table}
            self.assertTrue({"category=mixed", "condition=noisy", "accent=au"} <= groups)
            self.assertTrue((tmp / "out/summary.md").exists())
            self.assertTrue((tmp / "out/summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
