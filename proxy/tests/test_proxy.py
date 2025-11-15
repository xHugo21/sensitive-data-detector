from __future__ import annotations

import json
import main as proxy_main

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request


@pytest.fixture()
def client() -> TestClient:
    return TestClient(proxy_main.app)


def test_stringify_handles_nested_structures():
    payload = ["alpha", 42, {"text": "nested"}, None]

    assert (
        proxy_main._stringify(payload)  # pylint: disable=protected-access
        == "alpha\n42\nnested"
    )


def test_extract_payload_text_prefers_chat_messages():
    payload = {
        "messages": [
            {"role": "system", "content": "setup"},
            {"role": "user", "content": ["hello", {"text": "world"}]},
            {"role": "assistant", "content": "ignored"},
        ],
        "prompt": "fallback",
    }

    text = proxy_main._extract_payload_text(
        payload, "v1/chat/completions"
    )  # pylint: disable=protected-access

    assert text == "setup\n\nhello\nworld"


def test_extract_payload_text_uses_prompt_for_non_chat_path():
    payload = {"prompt": {"text": "linear"}}

    text = proxy_main._extract_payload_text(
        payload, "v1/completions"
    )  # pylint: disable=protected-access

    assert text == "linear"


def test_should_block_respects_threshold(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(proxy_main, "PROXY_MIN_BLOCK_RISK", "medium")

    assert proxy_main._should_block(
        {"risk_level": "High"}
    )  # pylint: disable=protected-access
    assert not proxy_main._should_block(
        {"risk_level": "Low"}
    )  # pylint: disable=protected-access


def test_detection_headers_include_detected_fields():
    result = {
        "risk_level": "High",
        "detected_fields": [
            {"field": "password"},
            {"field": "api_key"},
        ],
    }

    headers = proxy_main._detection_headers(result)  # pylint: disable=protected-access

    assert headers["X-LLM-Guard-Risk-Level"] == "High"
    assert "password" in headers["X-LLM-Guard-Detected-Fields"]
    assert "api_key" in headers["X-LLM-Guard-Detected-Fields"]


def test_proxy_error_response_contains_expected_payload():
    result = {"risk_level": "Medium", "detected_fields": [{"field": "ssn"}]}

    response = proxy_main._proxy_error_response(
        result
    )  # pylint: disable=protected-access

    assert response.status_code == 403
    body = json.loads(response.body)
    assert body["error"]["code"] == "sensitive_data"
    assert body["risk_level"] == "Medium"


def test_forward_headers_drops_hop_headers():
    scope = {
        "type": "http",
        "headers": [
            (b"host", b"example"),
            (b"x-token", b"abc"),
            (b"content-length", b"123"),
        ],
    }

    request = Request(scope)

    headers = proxy_main._forward_headers(request)  # pylint: disable=protected-access

    assert "x-token" in {k.lower(): v for k, v in headers.items()}
    assert "host" not in {k.lower(): v for k, v in headers.items()}
    assert "content-length" not in {k.lower(): v for k, v in headers.items()}


def test_proxy_request_blocks_when_detection_triggers(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    async def fake_ask_backend(_: str):
        return {
            "risk_level": "High",
            "detected_fields": [{"field": "password"}],
        }

    async def fake_forward_request(
        *_args, **_kwargs
    ):  # pragma: no cover - should not be called
        raise AssertionError("Upstream call should not happen when blocked")

    monkeypatch.setattr(
        proxy_main, "_ask_backend", fake_ask_backend
    )  # pylint: disable=protected-access
    monkeypatch.setattr(
        proxy_main, "_forward_request", fake_forward_request
    )  # pylint: disable=protected-access

    response = client.post(
        "/openai/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "secret"}]},
    )

    assert response.status_code == 403
    assert response.headers["X-LLM-Guard-Risk-Level"] == "High"
    assert response.json()["error"]["code"] == "sensitive_data"


def test_proxy_request_forwards_when_clear(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    async def fake_ask_backend(text: str):
        assert "hello" in text
        return {"risk_level": "None", "detected_fields": []}

    async def fake_forward_request(*_args, **_kwargs):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        return httpx.Response(
            status_code=201,
            content=b'{"echo": true}',
            headers={
                "content-type": "application/json",
                "x-upstream": "value",
                "connection": "keep-alive",
            },
            request=request,
        )

    monkeypatch.setattr(
        proxy_main, "_ask_backend", fake_ask_backend
    )  # pylint: disable=protected-access
    monkeypatch.setattr(
        proxy_main, "_forward_request", fake_forward_request
    )  # pylint: disable=protected-access

    response = client.post(
        "/openai/v1/chat/completions",
        json={"prompt": "hello"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 201
    assert response.json() == {"echo": True}
    assert response.headers["x-upstream"] == "value"


def test_proxy_request_rejects_streaming(client: TestClient):
    response = client.post(
        "/openai/v1/chat/completions",
        json={"stream": True},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Streaming requests are not supported."
