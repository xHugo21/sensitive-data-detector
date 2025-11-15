from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from config import (
    BACKEND_URL,
    BACKEND_DETECT_ENDPOINT,
    BACKEND_TIMEOUT_SECONDS,
    COPILOT_API_BASE,
    GROQ_API_BASE,
    OPENAI_API_BASE,
    PROXY_MIN_BLOCK_RISK,
    UPSTREAM_TIMEOUT_SECONDS,
)


app = FastAPI(title="LLM Guard External Proxy", version="0.1.0")

DETECT_URL = urljoin(f"{BACKEND_URL}/", BACKEND_DETECT_ENDPOINT.lstrip("/"))

TARGETS = {
    "openai": {"base_url": OPENAI_API_BASE, "display": "OpenAI"},
    "copilot": {"base_url": COPILOT_API_BASE, "display": "GitHub Copilot"},
    "groq": {"base_url": GROQ_API_BASE, "display": "Groq"},
}

_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

_RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(filter(None, (_stringify(item) for item in value)))
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
        return "\n".join(
            filter(None, (_stringify(item) for item in value.values()))
        )
    return ""


def _extract_payload_text(payload: Dict[str, Any], full_path: str) -> str:
    path_lower = full_path.lower()
    if "chat" in path_lower:
        messages = payload.get("messages")
        if isinstance(messages, list):
            chunks = []
            for item in messages:
                if not isinstance(item, dict):
                    continue
                role = item.get("role")
                if role not in {"user", "system"}:
                    continue
                text = _stringify(item.get("content"))
                if text:
                    chunks.append(text)
            if chunks:
                return "\n\n".join(chunks)
    prompt = payload.get("prompt")
    if prompt is not None:
        return _stringify(prompt)
    return ""


async def _ask_backend(text: str) -> Dict[str, Any]:
    if not text.strip():
        return {"detected_fields": [], "risk_level": "None"}
    data = {"text": text, "mode": "Zero-shot"}
    try:
        async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT_SECONDS) as client:
            response = await client.post(DETECT_URL, json=data)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Backend unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Backend error ({response.status_code}): {response.text}",
        )
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid JSON from backend") from exc


def _should_block(result: Dict[str, Any]) -> bool:
    threshold = _RISK_ORDER.get(PROXY_MIN_BLOCK_RISK, 1)
    if threshold <= 0:
        return False
    risk_level = (result.get("risk_level") or "none").strip().lower()
    return _RISK_ORDER.get(risk_level, 0) >= threshold


def _detection_headers(result: Dict[str, Any]) -> Dict[str, str]:
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


def _proxy_error_response(result: Dict[str, Any]) -> JSONResponse:
    payload = {
        "error": {
            "message": "Sensitive data detected. Request blocked.",
            "type": "sensitive_data_detected",
            "code": "sensitive_data",
        },
        "detected_fields": result.get("detected_fields", []),
        "risk_level": result.get("risk_level", "Unknown"),
    }
    return JSONResponse(
        status_code=403,
        content=payload,
        headers=_detection_headers(result),
    )


def _forward_headers(request: Request) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() in _HOP_HEADERS:
            continue
        headers[key] = value
    return headers


async def _forward_request(
    provider: str,
    full_path: str,
    method: str,
    headers: Dict[str, str],
    body: bytes,
) -> httpx.Response:
    base_url = TARGETS[provider]["base_url"].rstrip("/")
    target_url = f"{base_url}/{full_path}"
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
        return await client.request(method=method, url=target_url, headers=headers, content=body)


@app.api_route("/{provider}/{full_path:path}", methods=["POST"])
async def proxy_request(provider: str, full_path: str, request: Request):
    provider = provider.lower()
    if provider not in TARGETS:
        raise HTTPException(status_code=404, detail="Unknown provider alias")

    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8").strip() or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if bool(payload.get("stream")):
        raise HTTPException(status_code=400, detail="Streaming requests are not supported.")

    text_to_check = _extract_payload_text(payload, full_path)
    result = await _ask_backend(text_to_check)

    if _should_block(result):
        return _proxy_error_response(result)

    headers = _forward_headers(request)
    try:
        upstream = await _forward_request(provider, full_path, request.method, headers, body)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc

    response = Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )

    for key, value in upstream.headers.items():
        if key.lower() in _HOP_HEADERS:
            continue
        response.headers[key] = value

    for key, value in _detection_headers(result).items():
        response.headers[key] = value

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8787, reload=True)
