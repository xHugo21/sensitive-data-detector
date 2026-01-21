from __future__ import annotations

from .. import nodes
from .. import routers

NODE_REGISTRY = {
    "read_document": nodes.read_document,
    "llm_ocr_document": nodes.llm_ocr_document,
    "normalize": nodes.normalize,
    "run_dlp_detector": nodes.run_dlp_detector,
    "run_ner_detector": nodes.run_ner_detector,
    "merge_detections": nodes.merge_detections,
    "anonymize_text": nodes.anonymize_text,
    "evaluate_risk": nodes.evaluate_risk,
    "apply_policy": nodes.apply_policy,
    "run_llm_detector": nodes.run_llm_detector,
    "generate_remediation": nodes.generate_remediation,
}

ROUTER_REGISTRY = {
    "should_read_document": routers.should_read_document,
    "should_run_llm_ocr": routers.should_run_llm_ocr,
    "route_after_dlp_ner": routers.route_after_dlp_ner,
    "should_run_llm": routers.should_run_llm,
    "route_after_merge_final": routers.route_after_merge_final,
}
