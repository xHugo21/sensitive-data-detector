import ast
import os
import random
import time
from typing import List, Tuple

import pytest
from datasets import load_dataset

DATASET_LANGUAGES_ENV_VAR = "INTEGRATION_DATASET_LANGUAGES"
DATASET_MAX_CASES_ENV_VAR = "INTEGRATION_DATASET_MAX_CASES"
DATASET_SEED_ENV_VAR = "INTEGRATION_DATASET_SEED"

DATASET_NAME = "ai4privacy/pii-masking-200k"
DATASET_SPLIT = "train"
DATASET_TEXT_FIELD = "source_text"

DEFAULT_DATASET_LANGUAGES = "en"
DEFAULT_DATASET_MAX_CASES = 200
DEFAULT_DATASET_SEED = 1337

TYPE_ALIASES: dict[str, set[str]] = {
    "PERSON": {"FIRSTNAME", "LASTNAME", "MIDDLENAME", "PREFIX"},
    "NAME": {"FIRSTNAME", "LASTNAME", "MIDDLENAME"},
    "FULLNAME": {"FIRSTNAME", "LASTNAME", "MIDDLENAME"},
    "FIRSTNAME": {"PREFIX", "MIDDLENAME"},
    "ADDRESS": {
        "STREET",
        "BUILDINGNUMBER",
        "SECONDARYADDRESS",
        "CITY",
        "STATE",
        "COUNTY",
        "ZIPCODE",
    },
    "LOCATION": {"CITY", "STATE", "COUNTY", "NEARBYGPSCOORDINATE"},
    "CITY": {"FIRSTNAME"},
    "CREDITCARD": {"CREDITCARDNUMBER", "CREDITCARDCVV", "CREDITCARDISSUER"},
    "BANKACCOUNT": {"ACCOUNTNUMBER", "ACCOUNTNAME", "IBAN", "BIC"},
    "MONEY": {"AMOUNT", "CURRENCY", "CURRENCYCODE", "CURRENCYNAME", "CURRENCYSYMBOL"},
    "CURRENCY": {"CURRENCYCODE", "CURRENCYNAME", "CURRENCYSYMBOL"},
    "AMOUNT": {"CURRENCYSYMBOL", "CURRENCY", "CURRENCYCODE", "CURRENCYNAME"},
    "COMPANYNAME": {"JOBAREA", "JOBTITLE"},
    "IP": {"IPV4", "IPV6"},
    "IPADDRESS": {"IP", "IPV4", "IPV6"},
    "VEHICLE": {"VEHICLEVIN", "VEHICLEVRM"},
    "DATETIME": {"DATE", "TIME", "DOB"},
    "DATE": {"DOB"},
    "DOB": {"DATE"},
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
    if expected_upper in detected_upper:
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


def _parse_languages(value: str | None) -> list[str] | None:
    if value is None:
        return None
    languages = [lang.strip() for lang in value.split(",") if lang.strip()]
    return languages or None


def _parse_span_labels(span_labels: object, row_index: int) -> list[str]:
    if span_labels is None or span_labels == "":
        return []
    if isinstance(span_labels, str):
        try:
            spans = ast.literal_eval(span_labels)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"Row {row_index} has invalid span_labels: {exc}") from exc
    elif isinstance(span_labels, list):
        spans = span_labels
    else:
        raise ValueError(
            f"Row {row_index} has unsupported span_labels type: "
            f"{type(span_labels).__name__}"
        )

    labels: list[str] = []
    seen: set[str] = set()
    for span in spans:
        if not isinstance(span, (list, tuple)) or len(span) < 3:
            continue
        label = str(span[2]).strip()
        if not label or label.upper() == "O":
            continue
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def _load_dataset_cases() -> List[Tuple[str, str, List[str]]]:
    languages = _parse_languages(
        os.getenv(DATASET_LANGUAGES_ENV_VAR, DEFAULT_DATASET_LANGUAGES)
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

    if languages:
        dataset = dataset.filter(lambda row: row.get("language") in languages)

    if max_cases and max_cases > 0 and len(dataset) > max_cases:
        dataset = dataset.shuffle(seed=seed).select(range(max_cases))

    cases = []
    for index, row in enumerate(dataset):
        prompt = row.get(DATASET_TEXT_FIELD)
        if prompt is None:
            raise ValueError(f"Row {index} is missing '{DATASET_TEXT_FIELD}'.")
        expected_entities = _parse_span_labels(row.get("span_labels"), index)
        row_id = row.get("id")
        if row_id is None:
            test_id = f"row_{index:06d}"
        else:
            test_id = f"row_{int(row_id):06d}"
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
@pytest.mark.asyncio
async def test_sensitive_detection(
    orchestrator, pytestconfig, test_id, prompt, expected_entities
):
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
