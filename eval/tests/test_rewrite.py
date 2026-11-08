import csv
import json
import tempfile
import unittest
from pathlib import Path

from goftar_eval.bakeoff import load_jsonl
from goftar_eval.faithfulness import check, has_negation
from goftar_eval.prompts import build_user_message
from goftar_eval.rewrite_bakeoff import FileModel, run

CASES = Path(__file__).resolve().parent.parent / "corpus/llm_cases.jsonl"


class NegationTests(unittest.TestCase):
    def test_english(self):
        self.assertTrue(has_negation("We can't make Friday"))
        self.assertTrue(has_negation("This is not structural"))
        self.assertFalse(has_negation("We will send them on Monday"))

    def test_persian(self):
        self.assertTrue(has_negation("من فردا نمی‌تونم بیام"))
        self.assertTrue(has_negation("حالم خوب نیست"))
        self.assertTrue(has_negation("بتن‌ریزی را شروع نکنید"))
        self.assertFalse(has_negation("نقشه‌ها نیاز به اصلاح دارند"))


class CheckTests(unittest.TestCase):
    def test_good_translation_passes(self):
        r = check("لطفاً این Scope of Work رو برای Contractor آماده کن.",
                  "Please prepare this Scope of Work for the contractor.",
                  task="translate", output_lang="en", keep_terms=["Scope of Work", "Contractor"])
        self.assertTrue(r.passed, r.failures())

    def test_changed_number_fails(self):
        r = check("The quote came in at $45,000 plus GST.", "پیش‌فاکتور ۵۴٬۰۰۰ دلار به‌علاوه‌ی GST شد.",
                  task="translate", output_lang="fa", keep_terms=["GST"])
        self.assertEqual((r.numbers_missing, r.numbers_added), (["45000"], ["54000"]))
        self.assertFalse(r.passed)

    def test_persian_digits_count_as_same_number(self):
        r = check("The quote came in at $45,000 plus GST.", "پیش‌فاکتور ۴۵٬۰۰۰ دلار به‌علاوه‌ی GST شد.",
                  task="translate", output_lang="fa", keep_terms=["GST"])
        self.assertTrue(r.passed, r.failures())

    def test_dropped_negation_fails(self):
        r = check("Don't start the concrete pour until the engineer has signed off.",
                  "بتن‌ریزی را پس از تأیید مهندس شروع کنید.", task="translate", output_lang="fa")
        self.assertTrue(r.negation_mismatch)

    def test_self_correction_allowed(self):
        r = check("جلسه‌ی Site Meeting فردا ساعت ۹ نه ببخشید ساعت ۱۰ صبح برگزار می‌شه.",
                  "جلسه‌ی Site Meeting فردا ساعت ۱۰ صبح برگزار می‌شود.",
                  task="clean", output_lang="fa", keep_terms=["Site Meeting"], allow_dropped_numbers=["9"])
        # "نه" here is a correction, not negation; the checker flags it for review.
        self.assertEqual(r.numbers_missing, [])
        self.assertEqual(r.failures(), ["negation_mismatch"])

    def test_wrong_language_and_invention(self):
        r = check("yeah sounds good", "Sure! Here is a much longer reply that adds lots of new detail.",
                  task="clean", output_lang="fa")
        self.assertTrue(r.wrong_language)
        self.assertTrue(r.too_long)
        self.assertTrue(check("hi", "", task="clean", output_lang="en").empty)


class CaseFileTests(unittest.TestCase):
    def test_cases_valid(self):
        cases = load_jsonl(CASES)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for c in cases:
            self.assertIn(c["task"], {"clean", "professional", "translate"})
            self.assertIn(c["output_lang"], {"fa", "en"})
            self.assertIn("<dictation>", build_user_message(c))


class RunTests(unittest.TestCase):
    def test_run_with_file_model(self):
        cases = [c for c in load_jsonl(CASES) if c["id"] in {"tr02", "tr07"}]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            outputs = tmp / "m.jsonl"
            outputs.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
                {"id": "tr02", "text": "Please prepare this Scope of Work for the contractor.", "latency_ms": 400},
                {"id": "tr07", "text": "قیمت ۵۴٬۰۰۰ دلار به‌علاوه‌ی GST شد.", "latency_ms": 600},
            ]), encoding="utf-8")
            table, _ = run(cases, [FileModel(str(outputs))], tmp / "out")
            overall = table[0]
            self.assertEqual((overall["n"], overall["pass %"], overall["numbers_added"]), (2, 50.0, 1))
            with open(tmp / "out/rating_sheet.csv", encoding="utf-8-sig") as f:
                sheet = list(csv.DictReader(f))
            self.assertEqual({r["system"] for r in sheet}, {"A"})
            self.assertEqual(json.loads((tmp / "out/rating_key.json").read_text())["A"], "file:m")


if __name__ == "__main__":
    unittest.main()
