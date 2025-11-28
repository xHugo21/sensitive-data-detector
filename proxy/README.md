# Transparent Proxy for LLM API Sensitive Data Detection

A transparent HTTP/HTTPS proxy built with `mitmproxy` that intercepts LLM API requests and blocks requests containing sensitive data before they reach the API providers.

## Features

- **Transparent Interception**: Works system-wide via `HTTP_PROXY`/`HTTPS_PROXY` environment variables
- **Configurable Endpoints**: Define which API hosts and paths to monitor
- **Sensitive Data Detection**: Integrates with the sensitive-data-detector backend
- **Risk-Based Blocking**: Uses backend policy (configured via backend `MIN_BLOCK_RISK`)
- **Zero Code Changes**: No need to modify application code or API endpoints

> [!NOTE]
> Proxy only analyses prompt data from the role: 'user'. This avoids having false positives from system prompts included by external apps.

## Configuration

Copy `.env.example` to `.env` and configure its values:

```bash
cp .env.example .env
```

## Usage

### 1. Start the Backend

First, ensure the sensitive-data-detector backend is running

### 2. Start the Proxy

```bash
uv sync
uv run python -m app.main
```

### 3. Configure Your Environment

Set the proxy environment variables in your shell:

```bash
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080
```

### 4. HTTPS interception

If you have to intercept HTTPS traffic, you will have to add the mitmproxy certificate to trusted ones:

```bash
sudo cp mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates
```

Optionally, if you need to accept npm requests:

```bash
npm config set cafile ~/.mitmproxy/mitmproxy-ca-cert.pem
```

> [!WARNING]
> Remember to remove the cafile afterwards with ```bash npm config delete cafile```

### 5. Use Your LLM API Normally

Now any HTTP (or HTTPS) requests to configured endpoints will be intercepted:

If sensitive data is detected, the request will be blocked with a 403 response:

## How It Works

1. **Interception**: mitmproxy intercepts all HTTP/HTTPS requests
2. **Filtering**: Only requests to configured hosts/paths are analyzed
3. **Extraction**: Request payloads are parsed to extract text (chat messages, prompts)
4. **Detection**: Text is sent to the backend for sensitive data detection
5. **Blocking**: If risk level exceeds threshold, request is blocked with 403
6. **Forwarding**: Safe requests are forwarded to the original destination
7. **Headers**: Detection metadata is added to response headers

## Response Headers

The proxy adds detection metadata to response headers:

- **`X-LLM-Guard-Risk-Level`**: Detected risk level (None, Low, Medium, High)
- **`X-LLM-Guard-Detected-Fields`**: Comma-separated list of detected sensitive fields

## Limitations

- **Performance**: Each request incurs latency from backend detection call

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Local App   │────────▶│   Proxy      │────────▶│   LLM API    │
│              │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
                               │  ▲
                               │  |
                               ▼  |
                         ┌──────────────┐
                         │   Backend    │
                         │   Detector   │
                         └──────────────┘
```

## Manual test via cURL
After enabling the proxy the following cURL request should return a 403 HTTP response with the headers mentioned above and a descriptive error with the response from the multiagent-firewall

```bash
curl -v -x http://127.0.0.1:8080 \
  -X POST https://api.githubcopilot.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "My SSN is 123-45-6789"}]}'
```

## License

See LICENSE file in the root of the repository.
