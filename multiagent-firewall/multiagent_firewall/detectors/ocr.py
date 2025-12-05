from __future__ import annotations

import os
from typing import Any

from ..types import GuardState


class TesseractOCRDetector:
    """
    OCR detector using Tesseract
    """

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
        """
        Extract text from image file in state.
        Returns the extracted text as a plain string.
        """
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
    """
    LLM-based OCR detector
    """

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

        from langchain_litellm import ChatLiteLLM

        model_string = self._build_model_string()

        # Build client params
        client_params = {}
        if api_key:
            client_params["api_key"] = api_key
        if base_url:
            client_params["api_base"] = base_url

        self._llm = ChatLiteLLM(model=model_string, **client_params)

    def _build_model_string(self) -> str:
        """Build the model string with provider prefix."""
        # OpenAI doesn't need prefix
        if self.provider == "openai":
            return self.model
        # Other providers need prefix
        if self.model.startswith(f"{self.provider}/"):
            return self.model
        return f"{self.provider}/{self.model}"

    def __call__(self, state: GuardState) -> str:
        file_path = state.get("file_path")

        if not file_path:
            return ""

        if not os.path.exists(file_path):
            return ""

        try:
            import base64
            from langchain_core.messages import HumanMessage
            import mimetypes

            # Common image MIME types mapping (for formats not in mimetypes)
            IMAGE_MIME_TYPES = {
                ".webp": "image/webp",
                ".avif": "image/avif",
                ".heic": "image/heic",
                ".heif": "image/heif",
            }

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)

            if not mime_type or not mime_type.startswith("image/"):
                ext = os.path.splitext(file_path)[1].lower()
                mime_type = IMAGE_MIME_TYPES.get(ext, "image/jpeg")

            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            data_url = f"data:{mime_type};base64,{image_data}"

            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Extract all visible text from this image. Return only the text content you see, maintaining the original layout as much as possible. Do not provide explanations, descriptions, or any additional commentary.",
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )

            response = self._llm.invoke([message])

            if hasattr(response, "content"):
                content: Any = response.content
                if isinstance(content, str):
                    return content.strip()
                return ""
            return str(response).strip()

        except Exception as e:
            raise RuntimeError(f"LLM OCR failed to process image: {str(e)}") from e

    @classmethod
    def from_env(cls) -> "LLMOCRDetector":
        """
        Create LLM OCR detector from environment variables.
        Falls back to LLM_* variables if LLM_OCR_* not set.
        """
        provider = os.getenv("LLM_OCR_PROVIDER") or os.getenv("LLM_PROVIDER", "openai")
        model = os.getenv("LLM_OCR_MODEL") or os.getenv("LLM_MODEL", "gpt-4o")
        api_key = os.getenv("LLM_OCR_API_KEY") or os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_OCR_BASE_URL") or os.getenv("LLM_BASE_URL")

        if not api_key:
            raise RuntimeError(
                f"Missing API key for LLM OCR provider '{provider}'. "
                "Set LLM_OCR_API_KEY or LLM_API_KEY environment variable."
            )

        return cls(
            provider=provider.lower(),
            model=model,
            api_key=api_key,
            base_url=base_url,
        )


__all__ = ["TesseractOCRDetector", "LLMOCRDetector"]
