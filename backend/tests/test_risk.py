from app.core import risk


def test_compute_risk_level_high_for_sensitive_fields():
    fields = [{"field": "password"}]
    assert risk.compute_risk_level(fields) == "High"


def test_compute_risk_level_medium_for_accumulated_medium_fields():
    fields = [{"field": "email"}, {"field": "url"}]
    assert risk.compute_risk_level(fields) == "Medium"


def test_compute_risk_level_low_for_minor_fields():
    fields = [{"field": "first_name"}]
    assert risk.compute_risk_level(fields) == "Low"


def test_compute_risk_level_none_for_empty_list():
    assert risk.compute_risk_level([]) == "None"


def test_compute_risk_level_counts_unknown_fields_as_low():
    fields = [{"field": "custom-field"}]
    assert risk.compute_risk_level(fields) == "Low"
