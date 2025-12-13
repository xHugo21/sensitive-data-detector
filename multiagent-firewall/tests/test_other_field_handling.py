from multiagent_firewall.nodes.preprocessing import merge_detections


def test_merge_detections_relabels_unknown_llm_fields_to_other_and_high_risk():
    state = {
        "llm_fields": [{"field": "NAME", "value": "something", "source": "llm_detector"}],
        "dlp_fields": [],
    }
    merge_detections(state)
    assert state["detected_fields"][0]["field"] == "OTHER"
    assert state["detected_fields"][0]["risk"] == "high"
