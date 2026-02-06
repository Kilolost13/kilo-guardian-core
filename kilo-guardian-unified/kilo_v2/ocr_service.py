"""
OCR Service for document scanning using Tesseract.

Provides text extraction from images for medication bottles, receipts, and documents.
"""

import io
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

logger = logging.getLogger("OCRService")

# Try to import pytesseract
try:
    import pytesseract

    TESSERACT_AVAILABLE = True
    logger.info("✅ Tesseract OCR available")
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("⚠️ pytesseract not installed. Install with: pip install pytesseract")


class OCRService:
    """
    Service for extracting text from images using Tesseract OCR.

    Designed for tablet-based document scanning for TBI memory assistance:
    - Medication bottle labels
    - Receipts for expense tracking
    - General document scanning
    """

    def __init__(self):
        """Initialize OCR service."""
        self.available = TESSERACT_AVAILABLE

        if self.available:
            try:
                # Test Tesseract availability
                version = pytesseract.get_tesseract_version()
                logger.info(f"✅ Tesseract version: {version}")
            except Exception as e:
                logger.error(f"❌ Tesseract not properly installed: {e}")
                logger.error(
                    "Install Tesseract: sudo apt-get install tesseract-ocr (Linux)"
                )
                self.available = False

    def extract_text(
        self, image_data: bytes, lang: str = "eng", preprocessing: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text from image data.

        Args:
            image_data: Raw image bytes (JPEG, PNG, etc.)
            lang: Language for OCR (default: 'eng')
            preprocessing: Optional preprocessing ('auto', 'receipt', 'label')

        Returns:
            Dictionary with:
                - text: Extracted text
                - confidence: Average confidence score (0-100)
                - success: Boolean indicating success
                - error: Error message if failed
        """
        if not self.available:
            return {
                "success": False,
                "text": "",
                "confidence": 0,
                "error": "Tesseract OCR not available. Install pytesseract and tesseract-ocr.",
            }

        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if needed
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            # Apply preprocessing if specified
            if preprocessing:
                image = self._preprocess_image(image, preprocessing)

            # Extract text with confidence data
            text = pytesseract.image_to_string(image, lang=lang)

            # Get confidence scores
            try:
                data = pytesseract.image_to_data(
                    image, lang=lang, output_type=pytesseract.Output.DICT
                )
                confidences = [float(conf) for conf in data["conf"] if conf != -1]
                avg_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0
                )
            except Exception:
                avg_confidence = 0

            logger.info(
                f"✅ OCR extracted {len(text)} characters (confidence: {avg_confidence:.1f}%)"
            )

            return {
                "success": True,
                "text": text.strip(),
                "confidence": round(avg_confidence, 2),
                "error": None,
            }

        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            return {"success": False, "text": "", "confidence": 0, "error": str(e)}

    def _preprocess_image(self, image: Image.Image, mode: str) -> Image.Image:
        """
        Preprocess image for better OCR results.

        Args:
            image: PIL Image
            mode: Preprocessing mode ('auto', 'receipt', 'label')

        Returns:
            Preprocessed PIL Image
        """
        try:
            from PIL import ImageEnhance, ImageFilter

            if mode == "receipt":
                # Receipt: Increase contrast, sharpen
                image = ImageEnhance.Contrast(image).enhance(1.5)
                image = ImageEnhance.Sharpness(image).enhance(2.0)
                image = image.filter(ImageFilter.SHARPEN)

            elif mode == "label":
                # Medication label: Denoise, slight sharpening
                image = image.filter(ImageFilter.MedianFilter(size=3))
                image = ImageEnhance.Sharpness(image).enhance(1.3)

            elif mode == "auto":
                # Auto: Balanced preprocessing
                image = ImageEnhance.Contrast(image).enhance(1.2)
                image = ImageEnhance.Sharpness(image).enhance(1.5)

            logger.debug(f"Applied preprocessing: {mode}")
            return image

        except Exception as e:
            logger.warning(f"Preprocessing failed, using original image: {e}")
            return image

    def extract_from_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract text from image file.

        Args:
            file_path: Path to image file
            **kwargs: Additional arguments for extract_text()

        Returns:
            OCR result dictionary
        """
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
            return self.extract_text(image_data, **kwargs)
        except Exception as e:
            logger.error(f"❌ Failed to read file {file_path}: {e}")
            return {
                "success": False,
                "text": "",
                "confidence": 0,
                "error": f"Failed to read file: {e}",
            }


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get the global OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
