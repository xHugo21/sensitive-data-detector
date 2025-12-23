from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ..constants import REGEX_PATTERNS, KEYWORDS


def detect_keywords(
    text: str,
    keywords: Mapping[str, Sequence[str]] | None = None,
) -> List[Dict[str, Any]]:
    kw = keywords if keywords is not None else KEYWORDS

    findings: List[Dict[str, Any]] = []
    text_lower = text.lower()

    for field_name, keyword_list in kw.items():
        for keyword in keyword_list:
            if keyword.lower() in text_lower:
                findings.append(
                    {
                        "field": field_name,
                        "value": keyword,
                        "sources": ["dlp_keyword"],
                    }
                )

    return findings


def luhn_checksum(card_number: str) -> bool:
    """Validate credit card numbers using the Luhn algorithm."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13:
        return False

    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


def validate_iban(iban: str) -> bool:
    """Validate IBAN using the mod-97 algorithm."""
    iban = iban.replace(" ", "").replace("-", "").upper()

    if len(iban) < 15 or len(iban) > 34:
        return False

    if not (iban[:2].isalpha() and iban[2:4].isdigit()):
        return False

    rearranged = iban[4:] + iban[:4]

    numeric_string = ""
    for char in rearranged:
        if char.isdigit():
            numeric_string += char
        else:
            numeric_string += str(ord(char) - ord("A") + 10)

    return int(numeric_string) % 97 == 1


def validate_dni(dni: str) -> bool:
    """Validate Spanish DNI using the check letter algorithm."""
    dni = dni.upper().strip()

    if len(dni) != 9 or not dni[:8].isdigit() or not dni[8].isalpha():
        return False

    letters = "TRWAGMYFPDXBNJZSQVHLCKE"

    number = int(dni[:8])
    expected_letter = letters[number % 23]

    return dni[8] == expected_letter


def validate_ssn(ssn: str) -> bool:
    """Basic validation for US Social Security Numbers."""
    ssn_clean = ssn.replace("-", "").replace(" ", "")

    if len(ssn_clean) != 9 or not ssn_clean.isdigit():
        return False

    area = ssn_clean[:3]
    group = ssn_clean[3:5]
    serial = ssn_clean[5:]

    if area == "000" or area == "666" or int(area) >= 900:
        return False

    if group == "00":
        return False

    if serial == "0000":
        return False

    return True


def validate_vin(vin: str) -> bool:
    """Validate Vehicle Identification Number using check digit."""
    vin = vin.upper().replace(" ", "")

    if len(vin) != 17:
        return False

    if any(char in vin for char in "IOQ"):
        return False

    transliteration = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
        "H": 8,
        "J": 1,
        "K": 2,
        "L": 3,
        "M": 4,
        "N": 5,
        "P": 7,
        "R": 9,
        "S": 2,
        "T": 3,
        "U": 4,
        "V": 5,
        "W": 6,
        "X": 7,
        "Y": 8,
        "Z": 9,
    }

    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

    total = 0
    for i, char in enumerate(vin):
        if char.isdigit():
            value = int(char)
        else:
            value = transliteration.get(char, 0)
        total += value * weights[i]

    check_digit = total % 11
    check_char = "X" if check_digit == 10 else str(check_digit)

    return vin[8] == check_char


def detect_checksums(text: str) -> List[Dict[str, Any]]:
    """Detect sensitive data using checksum validation algorithms.

    This function reuses patterns from REGEX_PATTERNS and applies additional
    checksum validation to reduce false positives.
    """
    findings: List[Dict[str, Any]] = []

    # Credit card detection (Luhn algorithm)
    card_pattern = _extract_regex_pattern(REGEX_PATTERNS, "CREDITCARDNUMBER")
    if card_pattern:
        potential_cards = re.findall(card_pattern, text)
        for card in potential_cards:
            card_clean = card.replace(" ", "").replace("-", "")
            if luhn_checksum(card_clean):
                findings.append(
                    {
                        "field": "CREDITCARDNUMBER",
                        "value": card,
                        "sources": ["dlp_checksum"],
                    }
                )

    # IBAN detection (mod-97 algorithm)
    iban_pattern = _extract_regex_pattern(REGEX_PATTERNS, "IBAN")
    if iban_pattern:
        potential_ibans = re.findall(iban_pattern, text)
        for iban in potential_ibans:
            # Extract just the IBAN part (remove any captured groups)
            iban_str = iban[0] if isinstance(iban, tuple) else iban
            if validate_iban(iban_str):
                findings.append(
                    {
                        "field": "IBAN",
                        "value": iban_str,
                        "sources": ["dlp_checksum"],
                    }
                )

    # Spanish DNI detection (check letter algorithm)
    dni_pattern = _extract_regex_pattern(REGEX_PATTERNS, "DNI")
    if dni_pattern:
        potential_dnis = re.findall(dni_pattern, text.upper())
        for dni in potential_dnis:
            if validate_dni(dni):
                findings.append(
                    {
                        "field": "DNI",
                        "value": dni,
                        "sources": ["dlp_checksum"],
                    }
                )

    # SOCIALSECURITYNUMBER detection (validation rules)
    ssn_pattern = _extract_regex_pattern(REGEX_PATTERNS, "SOCIALSECURITYNUMBER")
    if ssn_pattern:
        potential_ssns = re.findall(ssn_pattern, text)
        for ssn in potential_ssns:
            if validate_ssn(ssn):
                findings.append(
                    {
                        "field": "SOCIALSECURITYNUMBER",
                        "value": ssn,
                        "sources": ["dlp_checksum"],
                    }
                )

    # VIN detection (check digit algorithm)
    vin_pattern = _extract_regex_pattern(REGEX_PATTERNS, "VEHICLEVIN")
    if vin_pattern:
        potential_vins = re.findall(vin_pattern, text.upper())
        for vin in potential_vins:
            if validate_vin(vin):
                findings.append(
                    {
                        "field": "VEHICLEVIN",
                        "value": vin,
                        "sources": ["dlp_checksum"],
                    }
                )

    return findings


def detect_regex_patterns(
    text: str,
    regex_patterns: Mapping[str, object] | None = None,
) -> List[Dict[str, Any]]:
    patterns = regex_patterns if regex_patterns is not None else REGEX_PATTERNS

    findings: List[Dict[str, Any]] = []
    if not text:
        return findings

    text_lower = text.lower()
    word_spans: List[Tuple[int, int]] | None = None

    for field_name, entry in patterns.items():
        rule = _normalize_regex_rule(field_name, entry)
        pattern = rule["regex"]
        keywords = rule["keywords"]
        window = rule["window"]
        keyword_matchers = _build_keyword_matchers(keywords) if keywords else []

        for match in re.finditer(pattern, text):
            value = _extract_match_value(match)
            cleaned = value.strip()
            if not cleaned:
                continue
            if keyword_matchers:
                if window <= 0:
                    continue
                if word_spans is None:
                    word_spans = _word_spans(text_lower)
                window_text = _extract_window_text(
                    text_lower, word_spans, match.span(), window
                )
                if not window_text or not _window_has_keyword(
                    window_text, keyword_matchers
                ):
                    continue
            findings.append(
                {
                    "field": rule["field"],
                    "value": cleaned,
                    "sources": ["dlp_regex"],
                }
            )

    return findings


def _extract_regex_pattern(
    patterns: Mapping[str, object], field_name: str
) -> str | None:
    entry = patterns.get(field_name)
    if entry is None:
        return None
    if isinstance(entry, str):
        return entry
    if isinstance(entry, Mapping):
        regex = entry.get("regex") or entry.get("pattern")
        if isinstance(regex, str):
            return regex
    return None


def _normalize_regex_rule(field_name: str, entry: object) -> Dict[str, Any]:
    if isinstance(entry, str):
        return {
            "field": field_name,
            "regex": entry,
            "window": 0,
            "keywords": [],
        }
    if isinstance(entry, Mapping):
        regex = entry.get("regex") or entry.get("pattern")
        if not isinstance(regex, str):
            raise ValueError(f"Regex pattern missing for field {field_name}")
        return {
            "field": entry.get("field", field_name),
            "regex": regex,
            "window": int(entry.get("window") or 0),
            "keywords": list(entry.get("keywords") or []),
        }
    raise ValueError(f"Invalid regex entry for field {field_name}")


def _extract_match_value(match: re.Match[str]) -> str:
    groups = match.groups()
    if groups:
        parts = [part if part is not None else "" for part in groups]
        return " ".join(parts)
    return match.group(0)


def _word_spans(text_lower: str) -> List[Tuple[int, int]]:
    return [m.span() for m in re.finditer(r"\b\w+\b", text_lower)]


def _extract_window_text(
    text_lower: str,
    word_spans: List[Tuple[int, int]],
    match_span: Tuple[int, int],
    window: int,
) -> str:
    if not word_spans:
        return ""
    match_start, match_end = match_span
    start_index = None
    end_index = None
    for i, (start, end) in enumerate(word_spans):
        if start_index is None and end >= match_start:
            start_index = i
        if start <= match_end:
            end_index = i
    if start_index is None:
        start_index = 0
    if end_index is None:
        end_index = start_index
    if end_index < start_index:
        end_index = start_index
    window_start = max(0, start_index - window)
    window_end = min(len(word_spans) - 1, end_index + window)
    char_start = word_spans[window_start][0]
    char_end = word_spans[window_end][1]
    return text_lower[char_start:char_end]


def _build_keyword_matchers(
    keywords: Iterable[str],
) -> List[Tuple[str, object]]:
    matchers: List[Tuple[str, object]] = []
    for keyword in keywords:
        kw = keyword.strip().lower()
        if not kw:
            continue
        if re.search(r"\W", kw):
            matchers.append(("substr", kw))
        else:
            matchers.append(("regex", re.compile(rf"\b{re.escape(kw)}\b")))
    return matchers


def _window_has_keyword(window_text: str, matchers: List[Tuple[str, object]]) -> bool:
    for kind, matcher in matchers:
        if kind == "substr":
            if matcher in window_text:
                return True
        elif matcher.search(window_text):
            return True
    return False


__all__ = ["detect_keywords", "detect_checksums", "detect_regex_patterns"]
