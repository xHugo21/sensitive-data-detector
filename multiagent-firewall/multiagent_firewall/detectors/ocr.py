from __future__ import annotations

import os
from typing import Any

from ..types import GuardState
from .utils import (
    build_chat_litellm,
    coerce_litellm_content_to_text,
    load_litellm_env,
)


class TesseractOCRDetector:
    """OCR detector using Tesseract"""

    def __init__(
        self,
        *,
        lang: str = "eng",
        config: str = "",
        confidence_threshold: int = 0,
        tesseract_cmd: str | None = None,
    ):
        self.lang = lang
        self.config = config
        self.confidence_threshold = confidence_threshold
        self.tesseract_cmd = tesseract_cmd

        if tesseract_cmd:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def __call__(self, state: GuardState) -> str:
        """Extract text from image file in state. Returns the extracted text as a plain string."""
        file_path = state.get("file_path")

        if not file_path:
            return ""

        if not os.path.exists(file_path):
            return ""

        try:
            import pytesseract
            from PIL import Image

            image = Image.open(file_path)

            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                config=self.config,
                output_type=pytesseract.Output.DICT,
            )

            text_parts = []

            # Process each detected text element
            n_boxes = len(ocr_data["text"])
            for i in range(n_boxes):
                text = ocr_data["text"][i].strip()
                conf = int(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0

                # Skip empty text or low confidence
                if not text or conf < self.confidence_threshold:
                    continue

                text_parts.append(text)

            return " ".join(text_parts)

        except Exception as e:
            raise RuntimeError(
                f"Tesseract OCR failed to process image: {str(e)}"
            ) from e

    # TODO: Same as LiteLLM, pass this arguments as parameters to the package instead of loading from env
    @classmethod
    def from_env(cls) -> "TesseractOCRDetector":
        """
        Create Tesseract OCR detector from environment variables.

        Environment variables:
            OCR_LANG: Tesseract language code (default: eng)
            OCR_CONFIG: Additional Tesseract config string (default: '')
            OCR_CONFIDENCE_THRESHOLD: Min confidence 0-100 (default: 0)
            TESSERACT_CMD: Path to tesseract binary (optional)
        """
        lang = os.getenv("OCR_LANG", "eng")
        config = os.getenv("OCR_CONFIG", "")

        threshold_str = os.getenv("OCR_CONFIDENCE_THRESHOLD", "0")
        try:
            threshold = int(threshold_str)
            # Clamp between 0 and 100
            threshold = max(0, min(100, threshold))
        except ValueError:
            threshold = 0

        tesseract_cmd = os.getenv("TESSERACT_CMD")

        return cls(
            lang=lang,
            config=config,
            confidence_threshold=threshold,
            tesseract_cmd=tesseract_cmd,
        )


class LLMOCRDetector:
    """LLM-based OCR detector"""

    def __init__(
        self,
        *,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

        client_params: dict[str, Any] = {}
        if api_key:
            client_params["api_key"] = api_key
        if base_url:
            client_params["api_base"] = base_url

        self._llm = build_chat_litellm(
            provider=self.provider, model=self.model, client_params=client_params
        )

    def __call__(self, state: GuardState) -> str:
        file_path = state.get("file_path")

        if not file_path:
            return ""

        if not os.path.exists(file_path):
            return ""

        try:
            import base64
            import mimetypes
            from langchain_core.messages import HumanMessage

            mime_type, _ = mimetypes.guess_type(file_path)

            # Default to image/jpeg if not recognized or not an image type
            if not mime_type or not mime_type.startswith("image/"):
                mime_type = "image/jpeg"

            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            data_url = f"data:{mime_type};base64,{image_data}"

            prompt = (
                "Extract all visible text from this image. Return only the text content you see, "
                "maintaining the original layout as much as possible. Do not provide explanations, "
                "descriptions, or any additional commentary."
            )
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )

            response = self._llm.invoke([message])
            return coerce_litellm_content_to_text(response)

        except Exception as e:
            raise RuntimeError(f"LLM OCR failed to process image: {str(e)}") from e

    @classmethod
    def from_env(cls) -> "LLMOCRDetector":
        """
        Create LLM OCR detector from environment variables.
        Falls back to LLM_* variables if LLM_OCR_* not set.
        """
        provider, model, client_params = load_litellm_env(
            prefix="LLM_OCR",
            fallback_prefix="LLM",
            default_provider="openai",
            default_model="gpt-4o",
            require_api_key=True,
        )
        api_key = client_params.get("api_key")
        if not api_key:
            raise RuntimeError("Missing API key for LLM OCR provider.")
        base_url = client_params.get("api_base")
        return cls(
            provider=provider,
            model=model,
            api_key=str(api_key),
            base_url=str(base_url) if base_url else None,
        )


__all__ = ["TesseractOCRDetector", "LLMOCRDetector"]
