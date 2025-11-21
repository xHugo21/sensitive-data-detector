from __future__ import annotations

import json
import re
from typing import Any, Dict

import httpx
from mitmproxy import http
from mitmproxy.http import HTTPFlow

from app import config


_RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


class SensitiveDataDetector:
    def __init__(self):
        self.intercepted_hosts = config.INTERCEPTED_HOSTS
        self.intercepted_paths = config.INTERCEPTED_PATHS

    def _should_intercept(self, flow: HTTPFlow) -> bool:
        if flow.request.method != "POST":
            return False

        host = flow.request.host.lower()
        if not any(host.endswith(h) for h in self.intercepted_hosts):
            return False

        path = flow.request.path.lower()
        if not any(path.startswith(p) for p in self.intercepted_paths):
            return False

        return True

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return "\n".join(filter(None, (self._stringify(item) for item in value)))
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                return text
            return "\n".join(
                filter(None, (self._stringify(item) for item in value.values()))
            )
        return ""

    def _clean_text(self, text: str) -> str:
        text = re.sub(
            r"<system-reminder>.*?</system-reminder>",  # Opencode CLI tags added inside user prompt
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return text.strip()

    def _extract_payload_text(self, payload: Dict[str, Any], path: str) -> str:
        path_lower = path.lower()
        if "chat" in path_lower:
            messages = payload.get("messages")
            if isinstance(messages, list):
                chunks = []
                for item in messages:
                    if not isinstance(item, dict):
                        continue
                    role = item.get("role")
                    if role != "user":
                        continue
                    text = self._stringify(item.get("content"))
                    if text:
                        chunks.append(self._clean_text(text))
                if chunks:
                    return "\n\n".join(chunks)
        prompt = payload.get("prompt")
        if prompt is not None:
            return self._clean_text(self._stringify(prompt))
        return ""

    def _ask_backend(self, text: str) -> Dict[str, Any] | None:
        if not text.strip():
            return {"detected_fields": [], "risk_level": "None"}

        data = {"text": text}
        if config.BACKEND_DETECTION_MODE:
            data["mode"] = config.BACKEND_DETECTION_MODE

        detect_url = (
            f"{config.BACKEND_URL}/{config.BACKEND_DETECT_ENDPOINT.lstrip('/')}"
        )

        try:
            with httpx.Client(timeout=config.BACKEND_TIMEOUT_SECONDS) as client:
                response = client.post(detect_url, json=data)

            if response.status_code >= 400:
                return None

            return response.json()
        except Exception:
            return None

    def _should_block(self, result: Dict[str, Any]) -> bool:
        threshold = _RISK_ORDER.get(config.PROXY_MIN_BLOCK_RISK, 1)
        if threshold <= 0:
            return False
        risk_level = (result.get("risk_level") or "none").strip().lower()
        return _RISK_ORDER.get(risk_level, 0) >= threshold

    def _detection_headers(self, result: Dict[str, Any]) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        risk = result.get("risk_level")
        if risk:
            headers["X-LLM-Guard-Risk-Level"] = str(risk)
        detected = result.get("detected_fields")
        if isinstance(detected, list) and detected:
            header_value = ", ".join(
                item.get("field", "unknown")
                for item in detected
                if isinstance(item, dict)
            )
            if header_value:
                headers["X-LLM-Guard-Detected-Fields"] = header_value
        return headers

    def _create_block_response(self, flow: HTTPFlow, result: Dict[str, Any]) -> None:
        detected = result.get("detected_fields", [])
        field_names = ", ".join(
            item.get("field", "unknown") for item in detected if isinstance(item, dict)
        )

        if field_names:
            message = f"[SensitiveDataDetectionProxy] Sensitive data detected: {field_names}. Request blocked."
        else:
            message = "[SensitiveDataDetectionProxy] Sensitive data detected. Request blocked."

        payload = {
            "error": {
                "message": message,
                "type": "sensitive_data_detected",
                "code": "sensitive_data",
            },
            "detected_fields": detected,
            "risk_level": result.get("risk_level", "Unknown"),
            "remediation": result.get("remediation", ""),
        }

        flow.response = http.Response.make(
            status_code=403,
            content=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **self._detection_headers(result),
            },
        )

    def request(self, flow: HTTPFlow) -> None:
        if not self._should_intercept(flow):
            return

        try:
            body_text = flow.request.content.decode("utf-8")
            payload = json.loads(body_text or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return

        text_to_check = self._extract_payload_text(payload, flow.request.path)
        result = self._ask_backend(text_to_check)

        if result is None:
            return

        if self._should_block(result):
            self._create_block_response(flow, result)
            return

    def response(self, flow: HTTPFlow) -> None:
        if not self._should_intercept(flow):
            return

        if not hasattr(flow, "_detection_result"):
            return

        for key, value in self._detection_headers(flow._detection_result).items():
            flow.response.headers[key] = value


addons = [SensitiveDataDetector()]
