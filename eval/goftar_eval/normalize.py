"""Text normalisation for scoring Persian, English and mixed transcripts.

Scoring should not punish differences that a reader would not notice, such as
Arabic vs Persian letter forms, Persian vs Latin digits, ZWNJ vs no ZWNJ,
punctuation and letter case.
"""

import re
import unicodedata

# Arabic code points that look like Persian letters.
_LETTER_MAP = str.maketrans({
    "ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه",
    "ؤ": "و", "إ": "ا", "أ": "ا", "ٱ": "ا",
})
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

ZWNJ = "‌"
_DIACRITICS = re.compile("[ً-ْٰـ]")  # harakat, superscript alef, tatweel
_BIDI_CONTROLS = re.compile("[‎‏‪-‮⁦-⁩]")
# Persian verb prefix written with a space instead of ZWNJ: "می خواهم" -> "میخواهم".
_MI_PREFIX = re.compile(r"(?<!\S)(ن?می) (?=\S)")
_THOUSANDS_SEP = re.compile(r"(?<=\d)[,٬](?=\d{3})")
_NON_WORD = re.compile(r"[^\w\s]")

_ARABIC_SCRIPT = re.compile("[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LATIN = re.compile("[A-Za-z]")


def normalize_digits(text: str) -> str:
    """Convert Persian/Arabic digits to Latin and drop thousands separators."""
    return _THOUSANDS_SEP.sub("", text.translate(DIGIT_MAP))


def normalize_for_scoring(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = _BIDI_CONTROLS.sub("", t)
    t = t.translate(_LETTER_MAP)
    t = normalize_digits(t)
    t = _DIACRITICS.sub("", t)
    t = t.replace(ZWNJ, "")
    t = _MI_PREFIX.sub(r"\1", t)
    t = t.lower()
    t = _NON_WORD.sub(" ", t)
    return " ".join(t.split())


def script_profile(text: str, min_share: float = 0.05) -> str:
    """Classify text as 'fa', 'en' or 'mixed' by its letters' scripts."""
    fa = len(_ARABIC_SCRIPT.findall(text))
    en = len(_LATIN.findall(text))
    total = fa + en
    if total == 0:
        return "unknown"
    minority = min(fa, en)
    if minority >= 2 and minority / total >= min_share:
        return "mixed"
    return "fa" if fa > en else "en"
