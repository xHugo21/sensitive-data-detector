from __future__ import annotations

import pytest
from multiagent_firewall.detectors.dlp import (
    detect_checksums,
    detect_keywords,
    detect_regex_patterns,
    luhn_checksum,
    validate_iban,
    validate_dni,
    validate_ssn,
    validate_vin,
)


def test_detect_keywords_default():
    text = """
    Here is my key:
    -----BEGIN PRIVATE KEY-----
    super-secret-material
    -----END PRIVATE KEY-----
    """
    findings = detect_keywords(text)

    assert len(findings) >= 1
    field_names = [f["field"] for f in findings]
    assert "SECRET" in field_names


def test_detect_keywords_custom():
    text = "This contains foo and bar"
    custom_keywords = {
        "CUSTOM_FIELD": ["foo", "bar"],
    }
    findings = detect_keywords(text, custom_keywords)

    assert len(findings) == 2
    assert all(f["field"] == "CUSTOM_FIELD" for f in findings)
    assert all(f["sources"] == ["dlp_keyword"] for f in findings)


def test_detect_keywords_case_insensitive():
    text = "ssh key header -----begin private key----- content"
    findings = detect_keywords(text)

    field_names = [f["field"] for f in findings]
    assert "SECRET" in field_names


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
    assert findings[0]["field"] == "CREDITCARDNUMBER"
    assert findings[0]["value"] == "4532015112830366"
    assert findings[0]["sources"] == ["dlp_checksum"]


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
    assert "PHONENUMBER" in field_names


def test_detect_regex_patterns_custom():
    text = "Order ID: ABC123"
    custom_patterns = {
        "ORDER_ID": {
            "field": "ORDER_ID",
            "regex": r"\b[A-Z]{3}\d{3}\b",
            "window": 0,
            "keywords": [],
        },
    }
    findings = detect_regex_patterns(text, custom_patterns)

    assert len(findings) == 1
    assert findings[0]["field"] == "ORDER_ID"
    assert findings[0]["value"] == "ABC123"
    assert findings[0]["sources"] == ["dlp_regex"]


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
        "EMAIL_PARTS": {
            "field": "EMAIL_PARTS",
            "regex": r"(\w+)@(\w+\.\w+)",
            "window": 0,
            "keywords": [],
        },
    }
    findings = detect_regex_patterns(text, custom_patterns)

    assert len(findings) == 1
    assert "test example.com" in findings[0]["value"]


def test_detect_regex_patterns_keyword_window_allows_match():
    text = "SSN: 123-45-6789"
    custom_patterns = {
        "SOCIALSECURITYNUMBER": {
            "field": "SOCIALSECURITYNUMBER",
            "regex": r"\b\d{3}-\d{2}-\d{4}\b",
            "window": 1,
            "keywords": ["ssn"],
        },
    }
    findings = detect_regex_patterns(text, custom_patterns)

    assert len(findings) == 1
    assert findings[0]["field"] == "SOCIALSECURITYNUMBER"


def test_detect_regex_patterns_keyword_window_blocks_match():
    text = "SSN data for records 123-45-6789"
    custom_patterns = {
        "SOCIALSECURITYNUMBER": {
            "field": "SOCIALSECURITYNUMBER",
            "regex": r"\b\d{3}-\d{2}-\d{4}\b",
            "window": 2,
            "keywords": ["ssn"],
        },
    }
    findings = detect_regex_patterns(text, custom_patterns)

    assert findings == []


# ============================================================================
# Extended Regex Pattern Tests
# ============================================================================


def test_detect_regex_ipv4():
    text = "Server IP is 192.168.1.1 and gateway is 10.0.0.1"
    findings = detect_regex_patterns(text)

    field_names = [f["field"] for f in findings]
    assert "IPV4" in field_names
    values = [f["value"] for f in findings if f["field"] == "IPV4"]
    assert "192.168.1.1" in values
    assert "10.0.0.1" in values


def test_detect_regex_ipv6():
    text = "IPv6 address: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    findings = detect_regex_patterns(text)

    field_names = [f["field"] for f in findings]
    assert "IPV6" in field_names


def test_detect_regex_mac_address():
    text = "MAC: 00:1A:2B:3C:4D:5E and 00-1A-2B-3C-4D-5F"
    findings = detect_regex_patterns(text)

    mac_findings = [f for f in findings if f["field"] == "MAC"]
    assert len(mac_findings) >= 1


def test_detect_regex_url():
    text = "Visit https://example.com or http://test.org"
    findings = detect_regex_patterns(text)

    field_names = [f["field"] for f in findings]
    assert "URL" in field_names


def test_detect_regex_credit_card():
    text = "Card: 4532-0151-1283-0366"
    findings = detect_regex_patterns(text)

    field_names = [f["field"] for f in findings]
    assert "CREDITCARDNUMBER" in field_names


def test_detect_regex_bitcoin_address():
    text = "Send BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    findings = detect_regex_patterns(text)

    field_names = [f["field"] for f in findings]
    assert "BITCOINADDRESS" in field_names


def test_detect_regex_ethereum_address():
    # Ethereum addresses are 42 characters (0x + 40 hex chars)
    text = "ETH wallet: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbC"
    findings = detect_regex_patterns(text)

    field_names = [f["field"] for f in findings]
    assert "ETHEREUMADDRESS" in field_names


def test_detect_regex_appointment_date():
    text = "Appointment on 2024-05-12"
    custom_patterns = {
        "APPOINTMENTDATE": {
            "field": "APPOINTMENTDATE",
            "regex": r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
            "window": 0,
            "keywords": [],
        },
    }
    findings = detect_regex_patterns(text, custom_patterns)

    field_names = [f["field"] for f in findings]
    assert "APPOINTMENTDATE" in field_names


# ============================================================================
# Extended Keyword Tests
# ============================================================================


def test_detect_keywords_ignores_generic_terms():
    text = "Enter your credentials to login with fingerprint and medical info"
    findings = detect_keywords(text)

    assert findings == []


# ============================================================================
# Checksum Validator Tests
# ============================================================================


def test_validate_iban_valid():
    assert validate_iban("GB82WEST12345698765432") is True
    assert validate_iban("DE89370400440532013000") is True
    assert validate_iban("FR1420041010050500013M02606") is True


def test_validate_iban_invalid():
    assert validate_iban("GB82WEST12345698765433") is False  # Wrong check digits
    assert validate_iban("XX123456789") is False  # Too short
    assert validate_iban("1234567890") is False  # Wrong format


def test_validate_dni_valid():
    assert validate_dni("12345678Z") is True
    assert validate_dni("87654321X") is True


def test_validate_dni_invalid():
    assert validate_dni("12345678A") is False  # Wrong letter
    assert validate_dni("1234567Z") is False  # Too short
    assert validate_dni("123456789") is False  # No letter


def test_validate_ssn_valid():
    assert validate_ssn("123-45-6789") is True
    assert validate_ssn("123 45 6789") is True
    assert validate_ssn("123456789") is True


def test_validate_ssn_invalid():
    assert validate_ssn("000-45-6789") is False  # Area 000
    assert validate_ssn("666-45-6789") is False  # Area 666
    assert validate_ssn("900-45-6789") is False  # Area 900+
    assert validate_ssn("123-00-6789") is False  # Group 00
    assert validate_ssn("123-45-0000") is False  # Serial 0000


def test_validate_vin_valid():
    # Note: These are example VINs with valid check digits
    assert validate_vin("1HGBH41JXMN109186") is True


def test_validate_vin_invalid():
    assert validate_vin("1HGBH41JXMN109187") is False  # Wrong check digit
    assert validate_vin("1HGBH41IXMN109186") is False  # Contains 'I'
    assert validate_vin("1HGBH41OXMN109186") is False  # Contains 'O'
    assert validate_vin("12345") is False  # Too short


# ============================================================================
# Extended Checksum Detection Tests
# ============================================================================


def test_detect_checksums_iban():
    text = "Transfer to IBAN: GB82WEST12345698765432"
    findings = detect_checksums(text)

    iban_findings = [f for f in findings if f["field"] == "IBAN"]
    assert len(iban_findings) == 1
    assert iban_findings[0]["sources"] == ["dlp_checksum"]


def test_detect_checksums_dni():
    text = "NATIONALID number: 12345678Z"
    findings = detect_checksums(text)

    dni_findings = [f for f in findings if f["field"] == "NATIONALID"]
    assert len(dni_findings) == 1
    assert dni_findings[0]["sources"] == ["dlp_checksum"]


def test_detect_checksums_ssn():
    text = "SOCIALSECURITYNUMBER: 123-45-6789"
    findings = detect_checksums(text)

    ssn_findings = [f for f in findings if f["field"] == "SOCIALSECURITYNUMBER"]
    assert len(ssn_findings) == 1
    assert ssn_findings[0]["sources"] == ["dlp_checksum"]


def test_detect_checksums_vin():
    text = "Vehicle VIN: 1HGBH41JXMN109186"
    findings = detect_checksums(text)

    vin_findings = [f for f in findings if f["field"] == "VEHICLEVIN"]
    assert len(vin_findings) == 1
    assert vin_findings[0]["sources"] == ["dlp_checksum"]


def test_detect_checksums_mixed():
    text = """
    Card: 4532015112830366
    IBAN: GB82WEST12345698765432
    NATIONALID: 12345678Z
    """
    findings = detect_checksums(text)

    assert len(findings) >= 3
    field_names = [f["field"] for f in findings]
    assert "CREDITCARDNUMBER" in field_names
    assert "IBAN" in field_names
    assert "NATIONALID" in field_names


def test_detect_checksums_invalid_mixed():
    text = """
    Invalid card: 1234567890123456
    Invalid IBAN: GB82WEST12345698765433
    Invalid NATIONALID: 12345678A
    """
    findings = detect_checksums(text)

    # Should not detect invalid data
    assert len(findings) == 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_integration_high_risk_data():
    text = """
    User credentials:
    -----BEGIN PRIVATE KEY-----
    mySecret123
    -----END PRIVATE KEY-----
    Credit Card: 4532-0151-1283-0366
    SOCIALSECURITYNUMBER: 123-45-6789
    """

    keyword_findings = detect_keywords(text)
    regex_findings = detect_regex_patterns(text)
    checksum_findings = detect_checksums(text)

    # Should detect multiple high-risk fields
    all_findings = keyword_findings + regex_findings + checksum_findings
    field_names = [f["field"] for f in all_findings]

    assert "SECRET" in field_names
    # Credit card and SOCIALSECURITYNUMBER should be detected by both regex and checksum
    assert "CREDITCARDNUMBER" in field_names
    assert "SOCIALSECURITYNUMBER" in field_names


def test_integration_medium_risk_data():
    text = """
    Contact information:
    Email: user@example.com
    Phone: +1-555-123-4567
    Company: Acme Corp
    """

    keyword_findings = detect_keywords(text)
    regex_findings = detect_regex_patterns(text)

    all_findings = keyword_findings + regex_findings
    field_names = [f["field"] for f in all_findings]

    assert "EMAIL" in field_names
    assert "PHONENUMBER" in field_names
    assert "SECRET" not in field_names
