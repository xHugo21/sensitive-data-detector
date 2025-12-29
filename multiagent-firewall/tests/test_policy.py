"""Tests for policy nodes (apply_policy and generate_remediation)."""

from multiagent_firewall.nodes.policy import apply_policy, generate_remediation


class TestApplyPolicy:
    """Test the apply_policy function."""

    def test_block_decision_when_risk_meets_threshold(self):
        """Test that block decision is set when risk meets or exceeds threshold."""
        state = {
            "risk_level": "high",
            "min_block_risk": "medium",
            "detected_fields": [
                {"field": "SSN", "value": "123-45-6789"}
            ],
        }
        result = apply_policy(state)
        assert result["decision"] == "block"

    def test_block_decision_with_exact_threshold_match(self):
        """Test block when risk level exactly matches threshold."""
        state = {
            "risk_level": "medium",
            "min_block_risk": "medium",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }
        result = apply_policy(state)
        assert result["decision"] == "block"

    def test_warn_decision_when_risk_below_threshold(self):
        """Test warn decision when fields detected but risk below threshold."""
        state = {
            "risk_level": "low",
            "min_block_risk": "medium",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }
        result = apply_policy(state)
        assert result["decision"] == "warn"

    def test_warn_decision_with_high_threshold(self):
        """Test warn when medium risk with high threshold."""
        state = {
            "risk_level": "medium",
            "min_block_risk": "high",
            "detected_fields": [{"field": "PHONENUMBER", "value": "123-456-7890"}],
        }
        result = apply_policy(state)
        assert result["decision"] == "warn"

    def test_allow_decision_when_no_detected_fields(self):
        """Test allow decision when no fields are detected."""
        state = {
            "risk_level": "none",
            "min_block_risk": "medium",
            "detected_fields": [],
        }
        result = apply_policy(state)
        assert result["decision"] == "allow"

    def test_allow_decision_with_none_risk_level(self):
        """Test allow when risk is none even with threshold."""
        state = {
            "risk_level": "none",
            "min_block_risk": "low",
            "detected_fields": [],
        }
        result = apply_policy(state)
        assert result["decision"] == "allow"

    def test_default_threshold_is_medium(self):
        """Test that default threshold is medium when not specified."""
        state = {
            "risk_level": "low",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }
        result = apply_policy(state)
        # Low risk with medium threshold (default) should warn
        assert result["decision"] == "warn"

    def test_block_overrides_warn_when_threshold_met(self):
        """Test that block takes precedence over warn."""
        state = {
            "risk_level": "high",
            "min_block_risk": "high",
            "detected_fields": [
                {"field": "SSN", "value": "123-45-6789"}
            ],
        }
        result = apply_policy(state)
        assert result["decision"] == "block"


class TestGenerateRemediation:
    """Test the generate_remediation function."""

    def test_block_remediation_message_format(self):
        """Test block remediation message contains correct fields and text."""
        state = {
            "decision": "block",
            "detected_fields": [
                {"field": "SSN", "value": "123-45-6789"},
                {"field": "PASSWORD", "value": "secret123"},
            ],
        }
        result = generate_remediation(state)

        assert "remediation" in result
        remediation = result["remediation"]
        assert "Sensitive data detected" in remediation
        assert "SSN" in remediation
        assert "PASSWORD" in remediation
        assert (
            "Redact or remove the flagged content before resubmitting." in remediation
        )

    def test_warn_remediation_message_format(self):
        """Test warn remediation message contains correct fields and advisory text."""
        state = {
            "decision": "warn",
            "detected_fields": [
                {"field": "EMAIL", "value": "test@example.com"},
                {"field": "PHONENUMBER", "value": "123-456-7890"},
            ],
        }
        result = generate_remediation(state)

        assert "remediation" in result
        remediation = result["remediation"]
        assert "Sensitive data detected" in remediation
        assert "EMAIL" in remediation
        assert "PHONENUMBER" in remediation
        assert (
            "Consider redacting or removing sensitive information before interacting with remote LLMs."
            in remediation
        )

    def test_warn_remediation_differs_from_block(self):
        """Test that warn message uses softer language than block."""
        state_warn = {
            "decision": "warn",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }
        state_block = {
            "decision": "block",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }

        result_warn = generate_remediation(state_warn)
        result_block = generate_remediation(state_block)

        # Both should mention sensitive data
        assert "Sensitive data detected" in result_warn["remediation"]
        assert "Sensitive data detected" in result_block["remediation"]

        # Warn uses "Consider"
        assert "Consider redacting" in result_warn["remediation"]
        assert "Consider redacting" not in result_block["remediation"]

        # Block uses "Redact or remove"
        assert "Redact or remove the flagged content" in result_block["remediation"]
        assert "Redact or remove the flagged content" not in result_warn["remediation"]

    def test_allow_remediation_is_empty(self):
        """Test that allow decision produces empty remediation."""
        state = {
            "decision": "allow",
            "detected_fields": [],
        }
        result = generate_remediation(state)

        assert "remediation" in result
        assert result["remediation"] == ""

    def test_remediation_with_single_field(self):
        """Test remediation message with single detected field."""
        state = {
            "decision": "warn",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }
        result = generate_remediation(state)

        assert "EMAIL" in result["remediation"]
        assert "Sensitive data detected (EMAIL)" in result["remediation"]

    def test_remediation_with_multiple_fields(self):
        """Test remediation message lists all unique field types."""
        state = {
            "decision": "block",
            "detected_fields": [
                {"field": "SSN", "value": "123-45-6789"},
                {"field": "EMAIL", "value": "test@example.com"},
                {"field": "PHONENUMBER", "value": "123-456-7890"},
                {
                    "field": "SSN",
                    "value": "987-65-4321",
                },  # Duplicate field type
            ],
        }
        result = generate_remediation(state)

        remediation = result["remediation"]
        # Should list unique field types
        assert "SSN" in remediation
        assert "EMAIL" in remediation
        assert "PHONENUMBER" in remediation
        # Should only appear once despite two SSN values
        assert remediation.count("SSN") == 1

    def test_remediation_with_unknown_field(self):
        """Test remediation handles fields without explicit field key."""
        state = {
            "decision": "warn",
            "detected_fields": [
                {"value": "some-value"},  # Missing 'field' key
                {"field": "EMAIL", "value": "test@example.com"},
            ],
        }
        result = generate_remediation(state)

        remediation = result["remediation"]
        assert "unknown" in remediation
        assert "EMAIL" in remediation

    def test_remediation_with_no_fields_uses_unspecified(self):
        """Test that empty detected_fields shows 'unspecified' in message."""
        state = {
            "decision": "block",
            "detected_fields": [],
        }
        result = generate_remediation(state)

        assert "unspecified" in result["remediation"]

    def test_remediation_preserves_other_state_fields(self):
        """Test that remediation doesn't remove other state fields."""
        state = {
            "decision": "warn",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
            "risk_level": "low",
            "other_field": "preserved",
        }
        result = generate_remediation(state)

        assert "remediation" in result
        assert result["risk_level"] == "low"
        assert result["other_field"] == "preserved"

    def test_warn_message_mentions_remote_llms(self):
        """Test that warn message specifically mentions remote LLMs."""
        state = {
            "decision": "warn",
            "detected_fields": [{"field": "PASSWORD", "value": "sk-1234"}],
        }
        result = generate_remediation(state)

        assert "remote LLMs" in result["remediation"]

    def test_block_message_does_not_mention_remote_llms(self):
        """Test that block message focuses on redaction before resubmitting."""
        state = {
            "decision": "block",
            "detected_fields": [
                {"field": "SSN", "value": "123-45-6789"}
            ],
        }
        result = generate_remediation(state)

        assert "remote LLMs" not in result["remediation"]
        assert "before resubmitting" in result["remediation"]


class TestPolicyIntegration:
    """Test apply_policy and generate_remediation working together."""

    def test_full_block_flow(self):
        """Test complete flow for block decision."""
        state = {
            "risk_level": "high",
            "min_block_risk": "medium",
            "detected_fields": [
                {"field": "SSN", "value": "123-45-6789"}
            ],
        }

        # Apply policy
        state = apply_policy(state)
        assert state["decision"] == "block"

        # Generate remediation
        state = generate_remediation(state)
        assert state["remediation"] != ""
        assert "SSN" in state["remediation"]
        assert "Redact or remove" in state["remediation"]

    def test_full_warn_flow(self):
        """Test complete flow for warn decision."""
        state = {
            "risk_level": "low",
            "min_block_risk": "high",
            "detected_fields": [{"field": "EMAIL", "value": "test@example.com"}],
        }

        # Apply policy
        state = apply_policy(state)
        assert state["decision"] == "warn"

        # Generate remediation
        state = generate_remediation(state)
        assert state["remediation"] != ""
        assert "EMAIL" in state["remediation"]
        assert "Consider redacting" in state["remediation"]
        assert "remote LLMs" in state["remediation"]

    def test_full_allow_flow(self):
        """Test complete flow for allow decision."""
        state = {
            "risk_level": "none",
            "min_block_risk": "medium",
            "detected_fields": [],
        }

        # Apply policy
        state = apply_policy(state)
        assert state["decision"] == "allow"

        # Generate remediation
        state = generate_remediation(state)
        assert state["remediation"] == ""
