from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Sequence

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
                        "source": "dlp_keyword",
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
    if "CREDITCARDNUMBER" in REGEX_PATTERNS:
        potential_cards = re.findall(REGEX_PATTERNS["CREDITCARDNUMBER"], text)
        for card in potential_cards:
            card_clean = card.replace(" ", "").replace("-", "")
            if luhn_checksum(card_clean):
                findings.append(
                    {
                        "field": "CREDITCARDNUMBER",
                        "value": card,
                        "source": "dlp_checksum",
                    }
                )

    # IBAN detection (mod-97 algorithm)
    if "IBAN" in REGEX_PATTERNS:
        potential_ibans = re.findall(REGEX_PATTERNS["IBAN"], text)
        for iban in potential_ibans:
            # Extract just the IBAN part (remove any captured groups)
            iban_str = iban[0] if isinstance(iban, tuple) else iban
            if validate_iban(iban_str):
                findings.append(
                    {
                        "field": "IBAN",
                        "value": iban_str,
                        "source": "dlp_checksum",
                    }
                )

    # Spanish DNI detection (check letter algorithm)
    if "DNI" in REGEX_PATTERNS:
        potential_dnis = re.findall(REGEX_PATTERNS["DNI"], text.upper())
        for dni in potential_dnis:
            if validate_dni(dni):
                findings.append(
                    {
                        "field": "DNI",
                        "value": dni,
                        "source": "dlp_checksum",
                    }
                )

    # SSN detection (validation rules)
    if "SSN" in REGEX_PATTERNS:
        potential_ssns = re.findall(REGEX_PATTERNS["SSN"], text)
        for ssn in potential_ssns:
            if validate_ssn(ssn):
                findings.append(
                    {
                        "field": "SSN",
                        "value": ssn,
                        "source": "dlp_checksum",
                    }
                )

    # VIN detection (check digit algorithm)
    if "VEHICLEVIN" in REGEX_PATTERNS:
        potential_vins = re.findall(REGEX_PATTERNS["VEHICLEVIN"], text.upper())
        for vin in potential_vins:
            if validate_vin(vin):
                findings.append(
                    {
                        "field": "VEHICLEVIN",
                        "value": vin,
                        "source": "dlp_checksum",
                    }
                )

    return findings


def detect_regex_patterns(
    text: str,
    regex_patterns: Mapping[str, str] | None = None,
) -> List[Dict[str, Any]]:
    patterns = regex_patterns if regex_patterns is not None else REGEX_PATTERNS

    findings: List[Dict[str, Any]] = []

    for field_name, pattern in patterns.items():
        for match in re.findall(pattern, text):
            value = match if isinstance(match, str) else " ".join(match)
            cleaned = value.strip()
            if not cleaned:
                continue
            findings.append(
                {
                    "field": field_name,
                    "value": cleaned,
                    "source": "dlp_regex",
                }
            )

    return findings


__all__ = ["detect_keywords", "detect_checksums", "detect_regex_patterns"]
