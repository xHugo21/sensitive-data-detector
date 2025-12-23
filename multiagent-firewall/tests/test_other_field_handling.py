from multiagent_firewall.nodes.preprocessing import merge_detections


def test_merge_detections_relabels_unknown_llm_fields_to_other_and_high_risk():
    state = {
        "llm_fields": [
            {"field": "NAME", "value": "something", "sources": ["llm_explicit"]}
        ],
        "dlp_fields": [],
    }
    merge_detections(state)
    assert state["detected_fields"][0]["field"] == "OTHER"
    assert state["detected_fields"][0]["risk"] == "high"


def test_merge_detections_accumulates_sources_for_duplicates():
    state = {
        "dlp_fields": [{"field": "TIME", "value": "13:15", "sources": ["dlp_regex"]}],
        "ner_fields": [{"field": "TIME", "value": "13:15", "sources": ["ner_gliner"]}],
    }
    merge_detections(state)
    assert len(state["detected_fields"]) == 1
    assert state["detected_fields"][0]["sources"] == ["dlp_regex", "ner_gliner"]
