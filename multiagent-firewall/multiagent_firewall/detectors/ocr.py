from __future__ import annotations

import os
from typing import Any, Dict, List

from ..types import GuardState, FieldList


class TesseractOCRDetector:
    """
    OCR detector using Tesseract OCR engine via pytesseract.
    
    Extracts text from images using the Tesseract OCR engine.
    Requires Tesseract binary to be installed on the system.
    
    Installation:
        Ubuntu/Debian: sudo apt-get install tesseract-ocr
        macOS: brew install tesseract
        Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
    
    Example:
        detector = TesseractOCRDetector(lang='eng', confidence_threshold=60)
        fields = detector(state)
    """

    def __init__(
        self,
        *,
        lang: str = "eng",
        config: str = "",
        confidence_threshold: int = 0,
        tesseract_cmd: str | None = None,
    ):
        """
        Initialize Tesseract OCR detector.
        
        Args:
            lang: Tesseract language code (default: 'eng')
            config: Additional Tesseract config string (default: '')
            confidence_threshold: Minimum confidence score 0-100 (default: 0)
            tesseract_cmd: Path to tesseract binary (default: auto-detect)
        """
        self.lang = lang
        self.config = config
        self.confidence_threshold = confidence_threshold
        self.tesseract_cmd = tesseract_cmd
        
        # Set tesseract command path if provided
        if tesseract_cmd:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def __call__(self, state: GuardState) -> FieldList:
        """
        Extract text from image file in state.
        
        Args:
            state: Guard state containing file_path to image
            
        Returns:
            List of detected text fields with confidence scores
        """
        file_path = state.get("file_path")
        
        if not file_path:
            return []
        
        if not os.path.exists(file_path):
            return []
        
        try:
            import pytesseract
            from PIL import Image
            
            # Open image
            image = Image.open(file_path)
            
            # Get detailed OCR data with confidence scores
            # Output: dict with keys: level, page_num, block_num, par_num, line_num,
            #         word_num, left, top, width, height, conf, text
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                config=self.config,
                output_type=pytesseract.Output.DICT
            )
            
            fields: FieldList = []
            
            # Process each detected text element
            n_boxes = len(ocr_data['text'])
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i]) if ocr_data['conf'][i] != '-1' else 0
                
                # Skip empty text or low confidence
                if not text or conf < self.confidence_threshold:
                    continue
                
                # Get bounding box coordinates
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                fields.append({
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
                        "level": ocr_data['level'][i],
                    }
                })
            
            return fields
            
        except Exception as e:
            # Raise error for document node to handle
            raise RuntimeError(f"Tesseract OCR failed to process image: {str(e)}") from e

    @classmethod
    def from_env(cls) -> "TesseractOCRDetector":
        """
        Create Tesseract OCR detector from environment variables.
        
        Environment variables:
            OCR_LANG: Tesseract language code (default: eng)
            OCR_CONFIG: Additional Tesseract config string (default: '')
            OCR_CONFIDENCE_THRESHOLD: Min confidence 0-100 (default: 0)
            TESSERACT_CMD: Path to tesseract binary (optional)
            
        Returns:
            Configured TesseractOCRDetector instance
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
