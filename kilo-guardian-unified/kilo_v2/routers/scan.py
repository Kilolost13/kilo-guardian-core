"""
Scan API Router - Document scanning and OCR endpoints.

Provides camera-based document scanning for:
- Medication bottle labels (Phase 2)
- Receipts for expense tracking (Phase 3)
- General text extraction (Phase 1)
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from kilo_v2.medication_parser import get_medication_parser
from kilo_v2.ocr_service import get_ocr_service
from kilo_v2.receipt_parser import get_receipt_parser

logger = logging.getLogger("ScanRouter")

router = APIRouter()


class OCRResult(BaseModel):
    """OCR extraction result."""

    success: bool
    text: str
    confidence: float
    error: Optional[str] = None


class MedicationScanResult(BaseModel):
    """Medication scan result with parsed structured data."""

    success: bool
    ocr_text: str
    ocr_confidence: float
    parsed_data: Dict[str, Any]
    form_data: Dict[str, str]
    parser_confidence: int
    error: Optional[str] = None


class ReceiptScanResult(BaseModel):
    """Receipt scan result with parsed expense data."""

    success: bool
    ocr_text: str
    ocr_confidence: float
    total: Optional[float]
    vendor: Optional[str]
    date: Optional[str]
    suggested_category: Optional[str]
    parser_confidence: int
    error: Optional[str] = None


class ScanStatus(BaseModel):
    """Scanner service status."""

    available: bool
    tesseract_installed: bool
    message: str


@router.get("/scan/status", response_model=ScanStatus)
def get_scan_status():
    """
    Check if OCR/scanning service is available.

    Returns:
        Status indicating if Tesseract is installed and ready
    """
    ocr = get_ocr_service()

    return ScanStatus(
        available=ocr.available,
        tesseract_installed=ocr.available,
        message="OCR service ready" if ocr.available else "Tesseract not installed",
    )


@router.post("/scan/extract", response_model=OCRResult)
async def extract_text_from_image(
    image: UploadFile = File(...),
    preprocessing: Optional[str] = Form(None),
    lang: str = Form("eng"),
):
    """
    Extract text from uploaded image using OCR.

    Args:
        image: Image file (JPEG, PNG, etc.)
        preprocessing: Optional preprocessing mode ('auto', 'receipt', 'label')
        lang: Language code for OCR (default: 'eng')

    Returns:
        OCR result with extracted text and confidence score
    """
    try:
        # Validate file type
        if not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {image.content_type}. Must be an image.",
            )

        # Read image data
        image_data = await image.read()

        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_data) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large: {len(image_data)} bytes. Max: {max_size} bytes.",
            )

        logger.info(f"Processing image: {image.filename} ({len(image_data)} bytes)")

        # Extract text
        ocr = get_ocr_service()
        result = ocr.extract_text(
            image_data=image_data, lang=lang, preprocessing=preprocessing
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        return OCRResult(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/quick", response_model=OCRResult)
async def quick_scan(image: UploadFile = File(...)):
    """
    Quick scan with automatic preprocessing.

    Convenience endpoint for simple text extraction without parameters.

    Args:
        image: Image file to scan

    Returns:
        OCR result with extracted text
    """
    return await extract_text_from_image(image=image, preprocessing="auto", lang="eng")


@router.post("/scan/medication", response_model=MedicationScanResult)
async def scan_medication(image: UploadFile = File(...)):
    """
    Scan medication bottle label and extract structured data.

    This endpoint:
    1. Performs OCR on the image (optimized for medication labels)
    2. Parses extracted text to find:
       - Drug name
       - Dosage (mg, mcg, IU, etc.)
       - Frequency (daily, twice daily, etc.)
       - Instructions (with food, before bed, etc.)
    3. Returns structured data ready for medication form pre-fill

    Args:
        image: Image file of medication bottle label

    Returns:
        Structured medication data with form-ready fields
    """
    try:
        # Validate file type
        if not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {image.content_type}. Must be an image.",
            )

        # Read image data
        image_data = await image.read()

        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_data) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large: {len(image_data)} bytes. Max: {max_size} bytes.",
            )

        logger.info(
            f"Scanning medication label: {image.filename} ({len(image_data)} bytes)"
        )

        # Step 1: OCR extraction (optimized for labels)
        ocr = get_ocr_service()
        ocr_result = ocr.extract_text(
            image_data=image_data,
            lang="eng",
            preprocessing="label",  # Use label-specific preprocessing
        )

        if not ocr_result["success"]:
            return MedicationScanResult(
                success=False,
                ocr_text="",
                ocr_confidence=0,
                parsed_data={},
                form_data={},
                parser_confidence=0,
                error=f"OCR failed: {ocr_result['error']}",
            )

        # Step 2: Parse extracted text
        parser = get_medication_parser()
        parsed_data = parser.parse(ocr_result["text"])

        # Step 3: Convert to form data
        form_data = parser.to_medication_form_data(parsed_data)

        logger.info(f"Medication parsed: {parsed_data['name']} {parsed_data['dosage']}")

        return MedicationScanResult(
            success=True,
            ocr_text=ocr_result["text"],
            ocr_confidence=ocr_result["confidence"],
            parsed_data=parsed_data,
            form_data=form_data,
            parser_confidence=parsed_data["confidence"],
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning medication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/receipt", response_model=ReceiptScanResult)
async def scan_receipt(image: UploadFile = File(...)):
    """
    Scan receipt and extract expense data for finance tracking.

    This endpoint:
    1. Performs OCR on the receipt image (optimized for receipts)
    2. Parses extracted text to find:
       - Total amount (primary focus)
       - Vendor/merchant name
       - Transaction date
       - Suggested category (Food, Gas, Medical, Bills, Other)
    3. Returns structured data ready for expense logging

    Args:
        image: Image file of receipt

    Returns:
        Structured receipt data with expense information
    """
    try:
        # Validate file type
        if not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {image.content_type}. Must be an image.",
            )

        # Read image data
        image_data = await image.read()

        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_data) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large: {len(image_data)} bytes. Max: {max_size} bytes.",
            )

        logger.info(f"Scanning receipt: {image.filename} ({len(image_data)} bytes)")

        # Step 1: OCR extraction (optimized for receipts)
        ocr = get_ocr_service()
        ocr_result = ocr.extract_text(
            image_data=image_data,
            lang="eng",
            preprocessing="receipt",  # Use receipt-specific preprocessing
        )

        if not ocr_result["success"]:
            return ReceiptScanResult(
                success=False,
                ocr_text="",
                ocr_confidence=0,
                total=None,
                vendor=None,
                date=None,
                suggested_category=None,
                parser_confidence=0,
                error=f"OCR failed: {ocr_result['error']}",
            )

        # Step 2: Parse extracted text
        parser = get_receipt_parser()
        parsed_data = parser.parse(ocr_result["text"])

        logger.info(
            f"Receipt parsed: {parsed_data['vendor']} - ${parsed_data['total']}"
        )

        return ReceiptScanResult(
            success=True,
            ocr_text=ocr_result["text"],
            ocr_confidence=ocr_result["confidence"],
            total=parsed_data["total"],
            vendor=parsed_data["vendor"],
            date=parsed_data["date"],
            suggested_category=parsed_data["suggested_category"],
            parser_confidence=parsed_data["confidence"],
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning receipt: {e}")
        raise HTTPException(status_code=500, detail=str(e))
