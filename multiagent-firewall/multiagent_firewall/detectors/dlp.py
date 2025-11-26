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
                findings.append({
                    "field": field_name,
                    "value": keyword,
                    "source": "dlp_keyword",
                })
    
    return findings


def luhn_checksum(card_number: str) -> bool:
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


def detect_checksums(text: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    
    card_pattern = r"\b\d{13,19}\b"
    potential_cards = re.findall(card_pattern, text)
    
    for card in potential_cards:
        card_clean = card.replace(" ", "").replace("-", "")
        if luhn_checksum(card_clean):
            findings.append({
                "field": "CREDITCARDNUMBER",
                "value": card,
                "source": "dlp_checksum",
            })
    
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
            findings.append({
                "field": field_name,
                "value": cleaned,
                "source": "dlp_regex",
            })
    
    return findings


__all__ = ["detect_keywords", "detect_checksums", "detect_regex_patterns"]
