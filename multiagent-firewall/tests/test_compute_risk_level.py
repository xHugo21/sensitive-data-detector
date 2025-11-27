from multiagent_firewall.nodes.risk import compute_risk_level


def test_compute_risk_level_high_for_sensitive_fields():
    """Test that a single high-risk field results in high risk level"""
    fields = [{"field": "password", "risk": "high"}]
    assert compute_risk_level(fields) == "high"


def test_compute_risk_level_medium_for_multiple_medium_fields():
    """Test that 2 medium-risk fields (2*2=4 points) result in medium risk level"""
    fields = [
        {"field": "email", "risk": "medium"}, 
        {"field": "url", "risk": "medium"}
    ]
    assert compute_risk_level(fields) == "medium"


def test_compute_risk_level_medium_for_accumulated_fields():
    """Test that 1 medium + 2 low fields (2+1+1=4 points) result in medium risk level"""
    fields = [
        {"field": "email", "risk": "medium"}, 
        {"field": "first_name", "risk": "low"},
        {"field": "last_name", "risk": "low"}
    ]
    assert compute_risk_level(fields) == "medium"


def test_compute_risk_level_low_for_single_medium_field():
    """Test that a single medium-risk field (2 points) results in low risk level"""
    fields = [{"field": "email", "risk": "medium"}]
    assert compute_risk_level(fields) == "low"


def test_compute_risk_level_low_for_minor_fields():
    """Test that low-risk fields result in low risk level"""
    fields = [{"field": "first_name", "risk": "low"}]
    assert compute_risk_level(fields) == "low"


def test_compute_risk_level_none_for_empty_list():
    """Test that no detected fields result in none risk level"""
    assert compute_risk_level([]) == "none"


def test_compute_risk_level_handles_missing_risk_field():
    """Test that fields without risk attribute are handled gracefully (contribute 0 points)"""
    fields = [{"field": "custom-field"}]  # Missing risk field
    assert compute_risk_level(fields) == "none"


def test_compute_risk_level_mixed_risks():
    """Test that mixed risk levels are scored correctly"""
    # 1 high (6) + 1 medium (2) + 1 low (1) = 9 points = high
    fields = [
        {"field": "password", "risk": "high"},
        {"field": "email", "risk": "medium"},
        {"field": "first_name", "risk": "low"}
    ]
    assert compute_risk_level(fields) == "high"


def test_compute_risk_level_threshold_boundaries():
    """Test risk level threshold boundaries"""
    # Exactly 6 points = high
    assert compute_risk_level([{"field": "password", "risk": "high"}]) == "high"
    
    # 5 points = medium (boundary)
    fields_5 = [
        {"field": "email1", "risk": "medium"},
        {"field": "email2", "risk": "medium"},
        {"field": "name", "risk": "low"}
    ]
    assert compute_risk_level(fields_5) == "medium"
    
    # 3 points = low
    fields_3 = [
        {"field": "name1", "risk": "low"},
        {"field": "name2", "risk": "low"},
        {"field": "name3", "risk": "low"}
    ]
    assert compute_risk_level(fields_3) == "low"


