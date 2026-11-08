"""Automatic checks that an AI rewrite or translation kept the user's meaning.

These checks are cheap and run on every output. They catch the most harmful
mistakes (changed numbers, lost names, flipped negation, wrong language); a
human still rates fluency and tone. The same checks will run in the product
before text is inserted (see plan §3.2).
"""

import re
from dataclasses import dataclass, field

from .metrics import number_diff, term_retention
from .normalize import normalize_for_scoring, script_profile

_EN_NEGATION = re.compile(r"\b(not|no|never|none|nothing|cannot)\b|n't\b", re.I)
# Persian negation: common negative verb prefixes and words. Deliberately short:
# a bare "ن" prefix would match ordinary words such as نیاز and نقشه.
_FA_NEG_WORDS = {"نه", "نیست", "نیستم", "نیستیم", "نیستند", "هیچ", "هرگز", "نباید"}
_FA_NEG_PREFIXES = ("نمی", "ندار", "نکن", "نشد", "نتون", "نتوان", "نخواه", "نبود", "نکرد", "نگذار", "نذار")


def has_negation(text: str) -> bool:
    if _EN_NEGATION.search(text):
        return True
    for word in re.split(r"[\s،؛؟.!,]+", text):
        if word in _FA_NEG_WORDS or word.startswith(_FA_NEG_PREFIXES):
            return True
    return False


def _output_lang_ok(output: str, expected: str) -> bool:
    profile = script_profile(output)
    if expected == "fa":
        return profile in ("fa", "mixed")  # Persian text may keep English terms
    return profile == "en"


@dataclass
class FaithfulnessResult:
    numbers_missing: list = field(default_factory=list)
    numbers_added: list = field(default_factory=list)
    terms_missing: list = field(default_factory=list)
    negation_mismatch: bool = False
    wrong_language: bool = False
    too_long: bool = False
    empty: bool = False

    @property
    def passed(self) -> bool:
        return not (self.numbers_missing or self.numbers_added or self.terms_missing
                    or self.negation_mismatch or self.wrong_language or self.too_long or self.empty)

    def failures(self) -> list[str]:
        names = []
        for name in ("numbers_missing", "numbers_added", "terms_missing"):
            if getattr(self, name):
                names.append(name)
        for name in ("negation_mismatch", "wrong_language", "too_long", "empty"):
            if getattr(self, name):
                names.append(name)
        return names


def check(source: str, output: str, *, task: str, output_lang: str,
          keep_terms=(), allow_dropped_numbers=()) -> FaithfulnessResult:
    r = FaithfulnessResult()
    if not output.strip():
        r.empty = True
        return r
    nums = number_diff(source, output)
    allowed = list(allow_dropped_numbers)
    for n in nums.missing:
        if n in allowed:
            allowed.remove(n)
        else:
            r.numbers_missing.append(n)
    r.numbers_added = nums.added
    padded = f" {normalize_for_scoring(output)} "
    r.terms_missing = [t for t in keep_terms if f" {normalize_for_scoring(t)} " not in padded]
    r.negation_mismatch = has_negation(source) != has_negation(output)
    r.wrong_language = not _output_lang_ok(output, output_lang)
    # Professional mode may add a greeting and sign-off; other tasks shouldn't grow much.
    limit = 4.0 if task == "professional" else 2.0
    src_words = max(len(normalize_for_scoring(source).split()), 1)
    r.too_long = len(normalize_for_scoring(output).split()) / src_words > limit
    return r


__all__ = ["check", "has_negation", "FaithfulnessResult", "term_retention"]
