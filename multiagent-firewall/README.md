# Multiagent Firewall for LLM Interactions

Multi-agent system that detects sensitive data in LLM prompts using a combination of DLP (Data Loss Prevention), OCR (Optical Character Recognition), LLM-based detection, and risk evaluation strategies.

## Architecture

The firewall uses a multi-agent architecture built on LangGraph with conditional routing for optimal performance:

```mermaid
flowchart TD
    Start(INPUT) --> HasFile{has file_path?}
    
    HasFile -->|Yes| Document[Document Parsing<br/>+ Tesseract OCR]
    HasFile -->|No| Normalize[Normalize<br/>Preprocess text]
    
    Document --> NeedsLLMOCR{Image and no<br/>text found?}
    NeedsLLMOCR -->|Yes| LLMOCR[LLM OCR<br/>Vision Model]
    NeedsLLMOCR -->|No| Normalize
    
    LLMOCR --> Normalize
    Normalize --> DLP[DLP Detector]
    
    DLP --> MergeDLP[Merge Detections]
    MergeDLP --> HasDLP{Any DLP hits?}
    HasDLP -->|Yes| RiskDLP[Risk Evaluation]
    HasDLP -->|No| ShouldAnonymize{Cloud LLM provider & ANONYMIZE_FOR_REMOTE_LLM true?}
    
    RiskDLP --> PolicyDLP[Policy Check]
    
    PolicyDLP --> DecisionBlock{Decision = block?}
    
    DecisionBlock -->|Yes| Remediation[Remediation]
    DecisionBlock -->|No| ShouldAnonymize
    
    ShouldAnonymize -->|Yes| Anonymize[Anonymize Detected Values]
    ShouldAnonymize -->|No| LLM[LLM Detector]
    Anonymize --> LLM[LLM Detector]
    
    LLM --> MergeFinal[Merge Detections]
    MergeFinal --> FinalRoute{LLM added new fields?}
    FinalRoute -->|No & prior decision| Remediation
    FinalRoute -->|Yes or no decision| RiskFinal[Risk Evaluation]
    RiskFinal --> PolicyFinal[Policy Check]
    
    PolicyFinal --> Remediation
    
    Remediation --> End(OUTPUT)
    
    style Start fill:#e1f5ff,stroke:#333,color:#000
    style End fill:#e1f5ff,stroke:#333,color:#000
    style HasFile fill:#fff4e6,stroke:#333,color:#000
    style NeedsLLMOCR fill:#fff4e6,stroke:#333,color:#000
    style HasDLP fill:#fff4e6,stroke:#333,color:#000
    style FinalRoute fill:#fff4e6,stroke:#333,color:#000
    style DecisionBlock fill:#fff4e6,stroke:#333,color:#000
    style Document fill:#e6f7ff,stroke:#333,color:#000
    style LLMOCR fill:#f0e6ff,stroke:#333,color:#000
    style ShouldAnonymize fill:#fff4e6,stroke:#333,color:#000
    style Anonymize fill:#f0e6ff,stroke:#333,color:#000
    style LLM fill:#f0e6ff,stroke:#333,color:#000
    style DLP fill:#e6ffe6,stroke:#333,color:#000
    style Remediation fill:#ffe6e6,stroke:#333,color:#000

```

## Usage

### Via the backend package
Our `backend/` package exposes an HTTP API that can be used to automatically call the multiagent pipeline.

### From another Python project

#### Text Detection
```python
from multiagent_firewall.orchestrator import GuardOrchestrator

orchestrator = GuardOrchestrator()

# Detect sensitive data in text
result = orchestrator.run(
  text="My SSN is 123-45-6789",
  llm_prompt="enriched-zero-shot"  # zero-shot, few-shot, or enriched-zero-shot
)

print(f"Decision: {result['decision']}")
print(f"Risk Level: {result['risk_level']}")
print(f"Detected Fields: {result['detected_fields']}")
```

#### PDF Detection
```python
from multiagent_firewall.orchestrator import GuardOrchestrator

orchestrator = GuardOrchestrator()

# Extracts text from PDF and detects sensitive data
result = orchestrator.run(file_path="/path/to/document.pdf")
```

#### Image Detection (OCR must be configured)
```python
from multiagent_firewall.orchestrator import GuardOrchestrator

orchestrator = GuardOrchestrator()

result = orchestrator.run(file_path="/path/to/screenshot.png")

print(f"Extracted Text: {result['raw_text'][:100]}...")
print(f"Risk Level: {result['risk_level']}")
print(f"Detected Fields: {result['detected_fields']}")
```

### Response Structure

The orchestrator returns a `GuardState` dictionary with:

```python
{
    "raw_text": str,              # Original input text
    "normalized_text": str,       # Preprocessed text
    "detected_fields": [          # List of detected sensitive fields
        {
            "type": str,          # Field type (SSN, EMAIL, etc.)
            "value": str,         # Detected value
            "confidence": float,  # Detection confidence (0-1)
            "source": str         # Detection source (dlp/llm)
        }
    ],
    "risk_level": str,            # None/Low/Medium/High
    "decision": str,              # allow/allow_with_warning/block
    "remediation": str            # Suggested action
}
```

## Configuration

### Environment Variables

#### LLM Configuration (Required)
```bash
LLM_PROVIDER=openai          # LLM provider (openai, ollama, etc.)
LLM_MODEL=gpt-4o-mini        # Model name
LLM_API_KEY=sk-xxx           # API key for the provider
LLM_BASE_URL=https://...     # Optional: custom API base URL
```

#### OCR Configuration (Optional)
```bash
OCR_LANG=eng                 # Tesseract language code (default: eng, more languages: install specific language for tesseract and add it (e.g: eng+esp))
OCR_CONFIDENCE_THRESHOLD=60  # Minimum confidence 0-100 (default: 0)
TESSERACT_CMD=/usr/bin/tesseract  # Custom Tesseract path
```

#### LLM OCR Fallback (Optional)

The firewall includes an intelligent OCR fallback system. When Tesseract OCR fails to extract text from an image, the system automatically falls back to using vision-capable LLMs.

```bash
LLM_OCR_PROVIDER=openai              # LLM provider (openai, anthropic, google, ollama, etc.)
LLM_OCR_MODEL=gpt-4o                 # Vision-capable model name
LLM_OCR_API_KEY=sk-xxx               # API key for the LLM provider
LLM_OCR_BASE_URL=https://...         # Custom API endpoint (optional)
```

#### LLM Prompt Template
```bash
LLM_PROMPT=zero-shot     # Options: zero-shot, enriched-zero-shot, few-shot, generic
```

#### Blocking Policy
```bash
MIN_BLOCK_RISK=medium        # Options: low, medium, high
```

### Supported File Types

- **Text files**: `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.yaml`, `.sh`, `.sql`
- **Documents**: `.pdf`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`
- **Code files**: `.js`, `.py`, `.java`, `.cpp`, `.c`, `.html`, `.css`

## Testing

### Unit Tests

```bash
uv sync --group test
```

```bash
uv run pytest
```

### Integration Tests

Integration tests run the full pipeline end-to-end with real LLM providers.

#### Setup

1. Create `.env` file in `integration_tests/`:

```bash
cd integration_tests
cp .env.example .env
```

2. Configure your LLM provider settings:

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=sk-your-actual-api-key-here
```

**Note:** For Ollama (local models), LLM_API_KEY is not needed but must have a random value

#### Running Integration Tests

```bash
cd integration_tests
./run_tests.sh
```

This will:
- Run all test cases against the full pipeline
- Calculate accuracy, precision, recall, and F1 metrics
- Cache results to avoid redundant LLM calls
