from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import NER_LABELS
from .detectors.utils import load_litellm_env


def _str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: str | None, default: float, *, min_value: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return max(min_value, parsed)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    client_params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRConfig:
    lang: str = "eng"
    config: str = ""
    confidence_threshold: int = 0
    tesseract_cmd: str | None = None


@dataclass(frozen=True)
class NERConfig:
    enabled: bool = False
    model: str = "urchade/gliner_multi-v2.1"
    labels: tuple[str, ...] = field(default_factory=lambda: tuple(NER_LABELS.keys()))
    label_map: Dict[str, str] = field(default_factory=lambda: dict(NER_LABELS))
    min_score: float = 0.5


@dataclass(frozen=True)
class GuardConfig:
    llm: LLMConfig
    llm_ocr: LLMConfig | None = None
    ocr: OCRConfig = field(default_factory=OCRConfig)
    ner: NERConfig = field(default_factory=NERConfig)
    debug: bool = False
    force_llm_detector: bool = False

    def llm_ocr_config(self) -> LLMConfig:
        """Return the OCR LLM config, falling back to the main LLM config."""
        return self.llm_ocr or self.llm

    @classmethod
    def from_env(cls) -> "GuardConfig":
        """
        Build GuardConfig from environment variables.

        The values are parsed once here; downstream code should not read os.environ.
        """
        llm_provider, llm_model, llm_client_params = load_litellm_env(
            prefix="LLM",
            require_api_key=True,
        )
        llm_config = LLMConfig(
            provider=llm_provider,
            model=llm_model,
            client_params=llm_client_params,
        )

        ocr_provider, ocr_model, ocr_client_params = load_litellm_env(
            prefix="LLM_OCR",
            fallback_prefix="LLM",
            require_api_key=True,
            fallback_extra_params=False,
        )
        llm_ocr_config = LLMConfig(
            provider=ocr_provider,
            model=ocr_model,
            client_params=ocr_client_params,
        )

        ocr_lang = os.getenv("OCR_LANG", "eng")
        ocr_config = os.getenv("OCR_CONFIG", "")
        threshold_str = os.getenv("OCR_CONFIDENCE_THRESHOLD", "0")
        try:
            threshold = int(threshold_str)
            threshold = max(0, min(100, threshold))
        except ValueError:
            threshold = 0
        tesseract_cmd = os.getenv("TESSERACT_CMD")

        debug_mode = _str_to_bool(os.getenv("DEBUG_MODE"), False)
        force_llm_detector = _str_to_bool(
            os.getenv("FORCE_LLM_DETECTOR"),
            False,
        )

        ner_enabled = _str_to_bool(os.getenv("NER_ENABLED"), False)
        ner_model = (os.getenv("NER_MODEL") or "urchade/gliner_multi-v2.1").strip()
        ner_min_score = _parse_float(
            os.getenv("NER_MIN_SCORE"),
            0.5,
            min_value=0.0,
        )
        ner_label_map = dict(NER_LABELS)

        return cls(
            llm=llm_config,
            llm_ocr=llm_ocr_config,
            ocr=OCRConfig(
                lang=ocr_lang,
                config=ocr_config,
                confidence_threshold=threshold,
                tesseract_cmd=tesseract_cmd,
            ),
            ner=NERConfig(
                enabled=ner_enabled,
                model=ner_model or "urchade/gliner_multi-v2.1",
                labels=tuple(NER_LABELS.keys()),
                label_map=ner_label_map,
                min_score=ner_min_score,
            ),
            debug=debug_mode,
            force_llm_detector=force_llm_detector,
        )
