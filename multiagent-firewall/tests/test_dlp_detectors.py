from __future__ import annotations

import pytest
from multiagent_firewall.detectors.dlp import (
    detect_checksums,
    detect_keywords,
    detect_regex_patterns,
    luhn_checksum,
)


def test_detect_keywords_default():
    text = "My api_key is secret123 and token is abc"
    findings = detect_keywords(text)
    
    assert len(findings) >= 3
    field_names = [f["field"] for f in findings]
    assert "API_KEY" in field_names
    assert "SECRET" in field_names
    assert "TOKEN" in field_names


def test_detect_keywords_custom():
    text = "This contains foo and bar"
    custom_keywords = {
        "CUSTOM_FIELD": ["foo", "bar"],
    }
    findings = detect_keywords(text, custom_keywords)
    
    assert len(findings) == 2
    assert all(f["field"] == "CUSTOM_FIELD" for f in findings)
    assert all(f["source"] == "dlp_keyword" for f in findings)


def test_detect_keywords_case_insensitive():
    text = "My API_KEY is here"
    findings = detect_keywords(text)
    
    field_names = [f["field"] for f in findings]
    assert "API_KEY" in field_names


def test_detect_keywords_empty_text():
    findings = detect_keywords("")
    assert findings == []


def test_luhn_checksum_valid():
    assert luhn_checksum("4532015112830366") is True
    assert luhn_checksum("5425233430109903") is True


def test_luhn_checksum_invalid():
    assert luhn_checksum("4532015112830367") is False
    assert luhn_checksum("1234567890123456") is False


def test_luhn_checksum_too_short():
    assert luhn_checksum("123") is False


def test_detect_checksums_valid_card():
    text = "My card number is 4532015112830366"
    findings = detect_checksums(text)
    
    assert len(findings) == 1
    assert findings[0]["field"] == "CREDIT_CARD"
    assert findings[0]["value"] == "4532015112830366"
    assert findings[0]["source"] == "dlp_checksum"


def test_detect_checksums_invalid_card():
    text = "Invalid card: 1234567890123456"
    findings = detect_checksums(text)
    
    assert len(findings) == 0


def test_detect_checksums_multiple_cards():
    text = "Cards: 4532015112830366 and 5425233430109903"
    findings = detect_checksums(text)
    
    assert len(findings) == 2


def test_detect_checksums_empty_text():
    findings = detect_checksums("")
    assert findings == []


def test_detect_regex_patterns_default():
    text = "Contact me at test@example.com or +1-555-123-4567"
    findings = detect_regex_patterns(text)
    
    assert len(findings) >= 2
    field_names = [f["field"] for f in findings]
    assert "EMAIL" in field_names
    assert "PHONE_NUMBER" in field_names


def test_detect_regex_patterns_custom():
    text = "Order ID: ABC123"
    custom_patterns = {
        "ORDER_ID": r"\b[A-Z]{3}\d{3}\b",
    }
    findings = detect_regex_patterns(text, custom_patterns)
    
    assert len(findings) == 1
    assert findings[0]["field"] == "ORDER_ID"
    assert findings[0]["value"] == "ABC123"
    assert findings[0]["source"] == "dlp_regex"


def test_detect_regex_patterns_empty_text():
    findings = detect_regex_patterns("")
    assert findings == []


def test_detect_regex_patterns_no_match():
    text = "No sensitive data here"
    findings = detect_regex_patterns(text)
    assert findings == []


def test_detect_regex_patterns_tuple_match():
    text = "test@example.com"
    custom_patterns = {
        "EMAIL_PARTS": r"(\w+)@(\w+\.\w+)",
    }
    findings = detect_regex_patterns(text, custom_patterns)
    
    assert len(findings) == 1
    assert "test example.com" in findings[0]["value"]
