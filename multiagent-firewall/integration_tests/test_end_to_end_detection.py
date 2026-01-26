import ast
import os
import random
import time
from typing import List, Tuple

import pytest
from datasets import load_dataset

DATASET_LOCALES_ENV_VAR = "INTEGRATION_DATASET_LOCALES"
DATASET_MAX_CASES_ENV_VAR = "INTEGRATION_DATASET_MAX_CASES"
DATASET_SEED_ENV_VAR = "INTEGRATION_DATASET_SEED"

DATASET_NAME = "nvidia/Nemotron-PII"
DATASET_SPLIT = "test"
DATASET_TEXT_FIELD = "text"

DEFAULT_DATASET_LOCALES = "us"
DEFAULT_DATASET_MAX_CASES = 200

# Mapping from nvidia snake_case labels to our UPPERCASE convention
LABEL_NORMALIZE: dict[str, str] = {
    "account_number": "ACCOUNT_NUMBER",
    "age": "AGE",
    "bank_routing_number": "BANK_ROUTING_NUMBER",
    "biometric_identifier": "BIOMETRIC_IDENTIFIER",
    "blood_type": "BLOOD_TYPE",
    "certificate_license_number": "CERTIFICATE_LICENSE_NUMBER",
    "city": "CITY",
    "company_name": "COMPANY_NAME",
    "coordinate": "COORDINATE",
    "country": "COUNTRY",
    "county": "COUNTY",
    "credit_debit_card": "CREDIT_DEBIT_CARD",
    "customer_id": "CUSTOMER_ID",
    "cvv": "CVV",
    "date": "DATE",
    "date_of_birth": "DATE_OF_BIRTH",
    "date_time": "DATE_TIME",
    "device_identifier": "DEVICE_IDENTIFIER",
    "education_level": "EDUCATION_LEVEL",
    "email": "EMAIL",
    "employee_id": "EMPLOYEE_ID",
    "employment_status": "EMPLOYMENT_STATUS",
    "fax_number": "FAX_NUMBER",
    "first_name": "FIRST_NAME",
    "gender": "GENDER",
    "health_plan_beneficiary_number": "HEALTH_PLAN_BENEFICIARY_NUMBER",
    "http_cookie": "HTTP_COOKIE",
    "ipv4": "IPV4",
    "language": "LANGUAGE",
    "last_name": "LAST_NAME",
    "license_plate": "LICENSE_PLATE",
    "mac_address": "MAC_ADDRESS",
    "medical_record_number": "MEDICAL_RECORD_NUMBER",
    "occupation": "OCCUPATION",
    "password": "PASSWORD",
    "phone_number": "PHONE_NUMBER",
    "pin": "PIN",
    "political_view": "POLITICAL_VIEW",
    "postcode": "POSTCODE",
    "race_ethnicity": "RACE_ETHNICITY",
    "religious_belief": "RELIGIOUS_BELIEF",
    "sexuality": "SEXUALITY",
    "ssn": "SSN",
    "state": "STATE",
    "street_address": "STREET_ADDRESS",
    "swift_bic": "SWIFT_BIC",
    "time": "TIME",
    "url": "URL",
    "user_name": "USER_NAME",
    "vehicle_identifier": "VEHICLE_IDENTIFIER",
}

# Type aliases for flexible matching between detected and expected types
TYPE_ALIASES: dict[str, set[str]] = {
    "PERSON": {"FIRST_NAME", "LAST_NAME"},
    "NAME": {"FIRST_NAME", "LAST_NAME"},
    "FULLNAME": {"FIRST_NAME", "LAST_NAME"},
    "FIRST_NAME": {"LAST_NAME"},
    "LAST_NAME": {"FIRST_NAME"},
    "ADDRESS": {"STREET_ADDRESS", "CITY", "STATE", "COUNTY", "POSTCODE", "COUNTRY"},
    "LOCATION": {"CITY", "STATE", "COUNTY", "COUNTRY", "COORDINATE"},
    "STREET_ADDRESS": {"CITY"},
    "PHONE": {"PHONE_NUMBER", "FAX_NUMBER"},
    "PHONE_NUMBER": {"FAX_NUMBER"},
    "FAX_NUMBER": {"PHONE_NUMBER"},
    "CARD": {"CREDIT_DEBIT_CARD", "CVV"},
    "SWIFT_BIC": {"BIC", "BANK_ROUTING_NUMBER"},
    "BIC": {"SWIFT_BIC"},
    "IP": {"IPV4", "IPV6"},
    "IP_ADDRESS": {"IPV4", "IPV6"},
    "IPV4": {"IPV6"},
    "MAC": {"MAC_ADDRESS"},
    "DOB": {"DATE_OF_BIRTH", "DATE"},
    "DATE_OF_BIRTH": {"DATE"},
    "DATE_TIME": {"DATE", "TIME"},
    "DATE": {"DATE_TIME", "DATE_OF_BIRTH"},
    "VIN": {"VEHICLE_IDENTIFIER"},
    "VEHICLE_VIN": {"VEHICLE_IDENTIFIER"},
    "ZIP": {"POSTCODE"},
    "ZIPCODE": {"POSTCODE"},
    "POSTCODE": {"ZIPCODE", "STATE"},
    "STATE": {"POSTCODE"},
    "SEXUALITY": {"GENDER"},
    "GENDER": {"SEXUALITY"},
    "OCCUPATION": {"EMPLOYMENT_STATUS"},
}

_REVERSE_ALIASES: dict[str, set[str]] = {}
for _detected, _expected_set in TYPE_ALIASES.items():
    for _expected in _expected_set:
        _REVERSE_ALIASES.setdefault(_expected, set()).add(_detected)


def _types_match(detected_type: str, expected_type: str) -> bool:
    """Check if detected type matches expected type with alias support."""
    detected_upper = detected_type.upper()
    expected_upper = expected_type.upper()

    # Exact match
    if detected_upper == expected_upper:
        return True

    # Substring match
    if expected_upper in detected_upper or detected_upper in expected_upper:
        return True

    # Alias match
    if detected_upper in TYPE_ALIASES:
        if expected_upper in TYPE_ALIASES[detected_upper]:
            return True

    # Reverse alias
    if expected_upper in _REVERSE_ALIASES:
        if detected_upper in _REVERSE_ALIASES[expected_upper]:
            return True

    return False


def _parse_locales(value: str | None) -> list[str] | None:
    if value is None:
        return None
    locales = [loc.strip() for loc in value.split(",") if loc.strip()]
    return locales or None


def _parse_spans(spans_data: object, row_index: int) -> list[str]:
    """Parse the spans field from nvidia dataset format."""
    if spans_data is None or spans_data == "" or spans_data == "[]":
        return []

    if isinstance(spans_data, str):
        try:
            spans = ast.literal_eval(spans_data)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"Row {row_index} has invalid spans: {exc}") from exc
    elif isinstance(spans_data, list):
        spans = spans_data
    else:
        raise ValueError(
            f"Row {row_index} has unsupported spans type: {type(spans_data).__name__}"
        )

    labels: list[str] = []
    seen: set[str] = set()
    for span in spans:
        if not isinstance(span, dict):
            continue
        label = span.get("label", "")
        if not label:
            continue
        label_str = str(label).strip().lower()
        normalized = LABEL_NORMALIZE.get(label_str, label_str.upper())
        if normalized not in seen:
            labels.append(normalized)
            seen.add(normalized)
    return labels


def _load_dataset_cases() -> List[Tuple[str, str, List[str]]]:
    locales = _parse_locales(
        os.getenv(DATASET_LOCALES_ENV_VAR, DEFAULT_DATASET_LOCALES)
    )

    max_cases_raw = os.getenv(DATASET_MAX_CASES_ENV_VAR)
    if max_cases_raw is None or not max_cases_raw.strip():
        max_cases = DEFAULT_DATASET_MAX_CASES
    else:
        max_cases = int(max_cases_raw)

    seed_raw = os.getenv(DATASET_SEED_ENV_VAR)
    if seed_raw is None or not seed_raw.strip():
        seed = random.randint(0, 2**32 - 1)
        os.environ[DATASET_SEED_ENV_VAR] = str(seed)
    else:
        seed = int(seed_raw)

    dataset = load_dataset(DATASET_NAME, split=DATASET_SPLIT)

    if locales:
        dataset = dataset.filter(lambda row: row.get("locale") in locales)

    if max_cases and max_cases > 0 and len(dataset) > max_cases:
        dataset = dataset.shuffle(seed=seed).select(range(max_cases))

    cases = []
    for index, row in enumerate(dataset):
        prompt = row.get(DATASET_TEXT_FIELD)
        if prompt is None:
            raise ValueError(f"Row {index} is missing '{DATASET_TEXT_FIELD}'.")
        expected_entities = _parse_spans(row.get("spans"), index)
        uid = row.get("uid")
        if uid is None:
            test_id = f"row_{index:06d}"
        else:
            test_id = f"uid_{uid[:8]}"
        cases.append((test_id, prompt, expected_entities))

    if not cases:
        raise ValueError("No test cases loaded from dataset.")
    return cases


TEST_CASES = _load_dataset_cases()


@pytest.mark.integration
@pytest.mark.parametrize(
    "test_id,prompt,expected_entities",
    TEST_CASES,
    ids=[case[0] for case in TEST_CASES],
)
@pytest.mark.asyncio(loop_scope="module")
async def test_sensitive_detection(
    orchestrator, pytestconfig, test_id, prompt, expected_entities
):
    if (
        hasattr(pytestconfig, "_integration_run_params")
        and "seed" not in pytestconfig._integration_run_params
    ):
        pytestconfig._integration_run_params["seed"] = os.getenv(DATASET_SEED_ENV_VAR)

    start_time = time.perf_counter()
    result = await orchestrator.run(text=prompt)
    duration_s = time.perf_counter() - start_time

    detected_fields = result.get("detected_fields", [])

    # Extract detected field types
    detected_types = [
        str(field.get("type", field.get("field", ""))).upper()
        for field in detected_fields
    ]
    expected_entities = [str(entity).upper() for entity in expected_entities]

    matched_expected = sum(
        1
        for expected in expected_entities
        if any(_types_match(detected, expected) for detected in detected_types)
    )
    unmatched_detected = {
        detected
        for detected in detected_types
        if not any(_types_match(detected, expected) for expected in expected_entities)
    }
    # Collect source statistics
    source_stats = {}
    for field in detected_fields:
        field_type = str(field.get("type", field.get("field", ""))).upper()
        is_tp = any(
            _types_match(field_type, expected) for expected in expected_entities
        )

        stat_key = "tp" if is_tp else "fp"

        for source in field.get("sources", []):
            if source not in source_stats:
                source_stats[source] = {"tp": 0, "fp": 0}
            source_stats[source][stat_key] += 1

    case_pass = (not expected_entities and not detected_fields) or (
        matched_expected == len(expected_entities)
    )
    pytestconfig._integration_metrics.append(
        {
            "tp": matched_expected,
            "fp": len(unmatched_detected),
            "fn": len(expected_entities) - matched_expected,
            "case_pass": case_pass,
            "duration_s": duration_s,
            "source_stats": source_stats,
        }
    )

    # Check that all expected entities are detected
    if expected_entities:
        for expected_entity in expected_entities:
            assert any(_types_match(dt, expected_entity) for dt in detected_types), (
                f"Test '{test_id}' failed.\n"
                f"Expected entity '{expected_entity}' not found.\n"
                f"Detected types: {detected_types}\n"
                f"Detected fields: {detected_fields}"
            )
    else:
        # If no expected entities, verify that no fields were detected
        assert len(detected_fields) == 0, (
            f"Test '{test_id}' failed.\n"
            f"Expected no entities, but detected: {detected_types}\n"
            f"Detected fields: {detected_fields}"
        )
