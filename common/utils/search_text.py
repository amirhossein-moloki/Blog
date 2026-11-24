"""
EN: Utilities for normalizing Persian, Arabic, English, digit, and ZWNJ variations in Blog search queries.
FA: ابزارهای یکسان‌سازی حروف فارسی/عربی، ارقام، نیم‌فاصله و نگارش‌های جایگزین برای جست‌وجوی بلاگ.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List

PERSIAN_TO_ASCII_DIGITS: Dict[str, str] = {
    "۰": "0",
    "۱": "1",
    "۲": "2",
    "۳": "3",
    "۴": "4",
    "۵": "5",
    "۶": "6",
    "۷": "7",
    "۸": "8",
    "۹": "9",
    "٠": "0",
    "١": "1",
    "٢": "2",
    "٣": "3",
    "٤": "4",
    "٥": "5",
    "٦": "6",
    "٧": "7",
    "٨": "8",
    "٩": "9",
}

ASCII_TO_PERSIAN_DIGITS: Dict[str, str] = {
    "0": "۰",
    "1": "۱",
    "2": "۲",
    "3": "۳",
    "4": "۴",
    "5": "۵",
    "6": "۶",
    "7": "۷",
    "8": "۸",
    "9": "۹",
}

ASCII_TO_ARABIC_DIGITS: Dict[str, str] = {
    "0": "٠",
    "1": "١",
    "2": "٢",
    "3": "٣",
    "4": "٤",
    "5": "٥",
    "6": "٦",
    "7": "٧",
    "8": "٨",
    "9": "٩",
}

CHAR_TRANSLATION_TABLE = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ے": "ی",
        "ې": "ی",
        "ۍ": "ی",
        "ك": "ک",
        "ڪ": "ک",
        "ګ": "ک",
        "أ": "ا",
        "إ": "ا",
        "ٱ": "ا",
        "ة": "ه",
        "ۀ": "ه",
        "\u200c": " ",  # ZWNJ -> space
        "\u200d": "",
        "\u200e": "",
        "\u200f": "",
        "\ufeff": "",
        "\u0640": "",  # Tatweel / Kashida
        **PERSIAN_TO_ASCII_DIGITS,
    }
)

ARABIC_VARIANT_TABLE = str.maketrans(
    {
        "ی": "ي",
        "ک": "ك",
    }
)

ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_search_text(text: str | None, *, strip_alef_madda: bool = True) -> str:
    """
    EN: Normalizes Persian/Arabic characters, digits, ZWNJ, and whitespace for consistent search matching.
    FA: حروف فارسی و عربی، ارقام، نیم‌فاصله و فاصله‌ها را برای تطبیق یکپارچه استاندارد می‌کند.
    """
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", str(text))
    cleaned = ARABIC_DIACRITICS_RE.sub("", cleaned)
    cleaned = cleaned.translate(CHAR_TRANSLATION_TABLE)
    if strip_alef_madda:
        cleaned = cleaned.replace("آ", "ا")
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip().lower()
    return cleaned


def _add_variant(bucket: List[str], seen: set[str], value: str) -> None:
    candidate = value.strip()
    if candidate and candidate not in seen:
        seen.add(candidate)
        bucket.append(candidate)


def build_persian_arabic_variants(text: str | None, max_variants: int = 12) -> List[str]:
    """
    EN: Generates Persian, Arabic, digit, ZWNJ, and compact variants for DB substring lookups.
    FA: نگارش‌های جایگزین فارسی/عربی، ارقام و نیم‌فاصله را برای جست‌وجوی دقیق در دیتابیس تولید می‌کند.
    """
    if not text or not str(text).strip():
        return []

    raw = str(text).strip()
    canonical = normalize_search_text(raw, strip_alef_madda=True)
    with_madda = normalize_search_text(raw, strip_alef_madda=False)

    variants: List[str] = []
    seen: set[str] = set()

    # Preserve raw input first (exact casing/punctuation), then normalized forms
    _add_variant(variants, seen, raw)
    _add_variant(variants, seen, raw.replace("\u200c", " "))
    _add_variant(variants, seen, raw.replace("\u200c", ""))
    _add_variant(variants, seen, canonical)
    _add_variant(variants, seen, with_madda)

    # Arabic letter variants (ی->ي, ک->ك)
    for base in (canonical, with_madda):
        if base:
            _add_variant(variants, seen, base.translate(ARABIC_VARIANT_TABLE))

    # ZWNJ & compact spacing variants for multi-word terms
    for base in (canonical, raw.replace("\u200c", " ")):
        if " " in base:
            _add_variant(variants, seen, base.replace(" ", "\u200c"))
            compact = base.replace(" ", "")
            if len(compact) >= 3:
                _add_variant(variants, seen, compact)

    # Persian and Arabic-Indic numeral variants when numbers are present
    if canonical and any(ch.isdigit() for ch in canonical):
        _add_variant(
            variants,
            seen,
            "".join(ASCII_TO_PERSIAN_DIGITS.get(ch, ch) for ch in canonical),
        )
        _add_variant(
            variants,
            seen,
            "".join(ASCII_TO_ARABIC_DIGITS.get(ch, ch) for ch in canonical),
        )

    return variants[:max_variants]
