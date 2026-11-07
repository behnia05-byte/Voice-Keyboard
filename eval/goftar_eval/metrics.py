"""Scoring metrics: word and character error rate, term retention, number checks."""

import re
from collections import Counter
from dataclasses import dataclass

from .normalize import normalize_digits, normalize_for_scoring


def _edit_distance(ref: list, hyp: list) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


@dataclass
class ErrorCount:
    errors: int
    ref_len: int

    @property
    def rate(self) -> float:
        return self.errors / self.ref_len if self.ref_len else 0.0


def word_errors(ref: str, hyp: str) -> ErrorCount:
    r, h = normalize_for_scoring(ref).split(), normalize_for_scoring(hyp).split()
    return ErrorCount(_edit_distance(r, h), len(r))


def char_errors(ref: str, hyp: str) -> ErrorCount:
    r = list(normalize_for_scoring(ref).replace(" ", ""))
    h = list(normalize_for_scoring(hyp).replace(" ", ""))
    return ErrorCount(_edit_distance(r, h), len(r))


def term_retention(terms: list[str], hyp: str) -> tuple[int, int]:
    """How many expected terms appear in the hypothesis, in their original script."""
    padded = f" {normalize_for_scoring(hyp)} "
    kept = sum(1 for t in terms if f" {normalize_for_scoring(t)} " in padded)
    return kept, len(terms)


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def extract_numbers(text: str) -> Counter:
    return Counter(_NUMBER.findall(normalize_digits(text)))


@dataclass
class NumberDiff:
    missing: list[str]
    added: list[str]
    ref_count: int

    @property
    def recall(self) -> float:
        if not self.ref_count:
            return 1.0
        return (self.ref_count - len(self.missing)) / self.ref_count


def number_diff(source: str, output: str) -> NumberDiff:
    """Numbers in source but not output, and numbers output invented.

    Also used later as the faithfulness check for AI rewrites.
    """
    src, out = extract_numbers(source), extract_numbers(output)
    return NumberDiff(
        missing=sorted((src - out).elements()),
        added=sorted((out - src).elements()),
        ref_count=sum(src.values()),
    )
