from __future__ import annotations

import os

from ..types import GuardState, FieldList


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

    def __call__(self, state: GuardState) -> FieldList:
        """
        Extract text from image file in state.
        Returns a list of detected text fields with confidence scores.
        """
        file_path = state.get("file_path")

        if not file_path:
            return []

        if not os.path.exists(file_path):
            return []

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

            fields: FieldList = []

            # Process each detected text element
            n_boxes = len(ocr_data["text"])
            for i in range(n_boxes):
                text = ocr_data["text"][i].strip()
                conf = int(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0

                # Skip empty text or low confidence
                if not text or conf < self.confidence_threshold:
                    continue

                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]
                h = ocr_data["height"][i]

                fields.append(
                    {
                        "field": "TEXT_IN_IMAGE",
                        "value": text,
                        "source": "ocr",
                        "confidence": conf,
                        "metadata": {
                            "bbox": {
                                "x": x,
                                "y": y,
                                "width": w,
                                "height": h,
                            },
                            "level": ocr_data["level"][i],
                        },
                    }
                )

            return fields

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


__all__ = ["TesseractOCRDetector"]
