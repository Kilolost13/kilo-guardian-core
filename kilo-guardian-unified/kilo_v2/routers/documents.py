"""
Documents API Router - General document scanning, storage, and search.

Provides endpoints for:
- Scanning/uploading documents (OCR + PDF storage)
- Keyword search in OCR text
- Voice search support ("show me my PT exercises")
- Document management (list, tag, delete)
- Local storage (no cloud)
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kilo_v2.db import get_session
from kilo_v2.models.document_models import Document
from kilo_v2.ocr_service import get_ocr_service


# Simple DB session helper (SQLAlchemy)
def get_document_db():
    return get_session()


logger = logging.getLogger("DocumentsRouter")

router = APIRouter()

# Document storage directory
DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "kilo_data/documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)


class DocumentScanRequest(BaseModel):
    """Request model for scanning a document."""

    title: Optional[str] = None
    category: str = "general"
    tags: Optional[str] = None  # Comma-separated tags


class DocumentScanResponse(BaseModel):
    """Response model for document scanning."""

    success: bool
    document_id: int
    title: str
    ocr_text: str
    ocr_confidence: float
    pdf_path: str
    message: str


class DocumentSearchResponse(BaseModel):
    """Response model for document search."""

    total_results: int
    documents: List[dict]


class DocumentUpdateRequest(BaseModel):
    """Request model for updating document metadata."""

    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None


@router.post("/documents/scan", response_model=DocumentScanResponse)
async def scan_document(
    image: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: str = Form("general"),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_document_db),
):
    """
    Scan a document and save as PDF with searchable OCR text.

    This endpoint:
    1. Performs OCR on the uploaded image
    2. Converts to PDF (or saves original PDF)
    3. Stores PDF file locally (kilo_data/documents/)
    4. Stores OCR text in database for search
    5. Returns document ID for future reference

    Args:
        image: Image or PDF file to scan
        title: Document title (optional, auto-generated if not provided)
        category: Category (medical, bills, letters, pt_exercises, etc.)
        tags: Comma-separated tags for organization
        db: Database session

    Returns:
        Document scan result with ID and OCR text
    """
    try:
        # Validate file type
        if not (
            image.content_type.startswith("image/")
            or image.content_type == "application/pdf"
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {image.content_type}. Must be an image or PDF.",
            )

        # Read file data
        file_data = await image.read()

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(file_data) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {len(file_data)} bytes. Max: {max_size} bytes.",
            )

        logger.info(f"Scanning document: {image.filename} ({len(file_data)} bytes)")

        # Step 1: Extract text with OCR (even if PDF, for searchability)
        ocr = get_ocr_service()

        # If image, perform OCR
        if image.content_type.startswith("image/"):
            ocr_result = ocr.extract_text(
                image_data=file_data, lang="eng", preprocessing="auto"
            )

            if not ocr_result["success"]:
                raise HTTPException(
                    status_code=500, detail=f"OCR failed: {ocr_result['error']}"
                )

            ocr_text = ocr_result["text"]
            ocr_confidence = ocr_result["confidence"]

            # Convert image to PDF using img2pdf
            try:
                import img2pdf

                pdf_data = img2pdf.convert(file_data)
            except Exception as e:
                logger.warning(f"Failed to convert to PDF: {e}, saving as image")
                pdf_data = file_data

        elif image.content_type == "application/pdf":
            # Already a PDF, try to extract text
            try:
                import PyPDF2

                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
                ocr_text = ""
                for page in pdf_reader.pages:
                    ocr_text += page.extract_text()

                ocr_confidence = 90.0 if ocr_text.strip() else 0.0
                pdf_data = file_data
            except Exception as e:
                logger.warning(f"Failed to extract text from PDF: {e}")
                ocr_text = ""
                ocr_confidence = 0.0
                pdf_data = file_data

        # Step 2: Generate title if not provided
        if not title:
            # Auto-generate from filename or first line of OCR text
            if image.filename and image.filename != "blob":
                title = os.path.splitext(image.filename)[0][:200]
            elif ocr_text:
                # Use first non-empty line (up to 100 chars)
                first_line = ocr_text.split("\n")[0].strip()[:100]
                title = first_line if first_line else f"{category.title()} Document"
            else:
                title = f"{category.title()} Document"

        # Step 3: Save PDF file to filesystem
        # Organize by year/month for easier browsing
        now = datetime.utcnow()
        year_month_dir = os.path.join(DOCUMENTS_DIR, str(now.year), f"{now.month:02d}")
        os.makedirs(year_month_dir, exist_ok=True)

        # Generate unique filename
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:50]
        filename = f"{timestamp}_{safe_title}.pdf"
        file_path = os.path.join(year_month_dir, filename)

        # Write PDF to disk
        with open(file_path, "wb") as f:
            f.write(pdf_data)

        # Get relative path for database
        relative_path = os.path.relpath(file_path, start="kilo_data")

        logger.info(f"Saved PDF to: {file_path}")

        # Step 4: Save document metadata to database
        document = Document(
            title=title,
            category=category,
            tags=tags if tags else "",
            ocr_text=ocr_text,
            ocr_confidence=int(ocr_confidence),
            pdf_path=relative_path,
            original_filename=image.filename,
            file_size=len(file_data),
            scan_date=now,
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(f"Document saved: ID={document.id}, title='{title}'")

        return DocumentScanResponse(
            success=True,
            document_id=document.id,
            title=title,
            ocr_text=ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text,
            ocr_confidence=ocr_confidence,
            pdf_path=relative_path,
            message=f"Document '{title}' scanned and saved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning document: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/search", response_model=DocumentSearchResponse)
def search_documents(
    query: str = Query(..., min_length=2),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_document_db),
):
    """
    Search documents by keyword (supports voice search).

    Voice search examples:
    - "show me my PT exercises" → query="PT exercises"
    - "find my medical bills" → query="medical bills", category="bills"
    - "where are my knee instructions" → query="knee instructions"

    Args:
        query: Search keywords (searches in title, tags, and OCR text)
        category: Optional category filter
        limit: Maximum results to return (default: 50)
        db: Database session

    Returns:
        List of matching documents with relevance ranking
    """
    try:
        # Build search query
        search_query = db.query(Document).filter(Document.is_archived == False)

        # Category filter
        if category:
            search_query = search_query.filter(Document.category == category)

        # Keyword search (case-insensitive, searches title, tags, and OCR text)
        keywords = query.lower().split()

        # Use SQL LIKE for each keyword (searches in multiple fields)
        for keyword in keywords:
            search_filter = (
                Document.title.ilike(f"%{keyword}%")
                | Document.tags.ilike(f"%{keyword}%")
                | Document.ocr_text.ilike(f"%{keyword}%")
            )
            search_query = search_query.filter(search_filter)

        # Execute query
        results = search_query.order_by(Document.scan_date.desc()).limit(limit).all()

        logger.info(f"Document search: query='{query}', found {len(results)} results")

        return DocumentSearchResponse(
            total_results=len(results), documents=[doc.to_dict() for doc in results]
        )

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/list", response_model=List[dict])
def list_documents(
    category: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    favorites_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_document_db),
):
    """
    List all documents with optional filters.

    Args:
        category: Filter by category
        include_archived: Include archived documents
        favorites_only: Show only favorited documents
        limit: Maximum results
        db: Database session

    Returns:
        List of documents
    """
    try:
        query = db.query(Document)

        # Filters
        if not include_archived:
            query = query.filter(Document.is_archived == False)

        if category:
            query = query.filter(Document.category == category)

        if favorites_only:
            query = query.filter(Document.is_favorite == True)

        # Execute
        documents = query.order_by(Document.scan_date.desc()).limit(limit).all()

        return [doc.to_dict() for doc in documents]

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/pdf")
def get_document_pdf(document_id: int, db: Session = Depends(get_document_db)):
    """
    Download document PDF file.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        PDF file download
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Build full path
        full_path = os.path.join("kilo_data", document.pdf_path)

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk")

        # Return file
        return FileResponse(
            path=full_path,
            media_type="application/pdf",
            filename=f"{document.title}.pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", response_model=dict)
def get_document(document_id: int, db: Session = Depends(get_document_db)):
    """
    Get document details by ID.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        Document metadata and full OCR text
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Return full document (including complete OCR text)
        result = document.to_dict()
        result["ocr_text_full"] = document.ocr_text  # Include full text
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/documents/{document_id}", response_model=dict)
def update_document(
    document_id: int,
    update: DocumentUpdateRequest,
    db: Session = Depends(get_document_db),
):
    """
    Update document metadata (title, tags, category, etc.).

    Args:
        document_id: Document ID
        update: Fields to update
        db: Database session

    Returns:
        Updated document
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update fields
        if update.title is not None:
            document.title = update.title
        if update.category is not None:
            document.category = update.category
        if update.tags is not None:
            document.tags = update.tags
        if update.is_favorite is not None:
            document.is_favorite = update.is_favorite
        if update.is_archived is not None:
            document.is_archived = update.is_archived

        document.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(document)

        logger.info(f"Document {document_id} updated")

        return document.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", response_model=dict)
def delete_document(
    document_id: int,
    permanent: bool = Query(False),
    db: Session = Depends(get_document_db),
):
    """
    Delete document (archive or permanent).

    Args:
        document_id: Document ID
        permanent: If True, delete PDF file and database record
                  If False, just mark as archived
        db: Database session

    Returns:
        Success confirmation
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if permanent:
            # Delete PDF file from disk
            full_path = os.path.join("kilo_data", document.pdf_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted PDF file: {full_path}")

            # Delete database record
            db.delete(document)
            db.commit()

            logger.info(f"Document {document_id} permanently deleted")

            return {
                "success": True,
                "message": f"Document '{document.title}' permanently deleted",
            }
        else:
            # Just mark as archived
            document.is_archived = True
            document.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Document {document_id} archived")

            return {"success": True, "message": f"Document '{document.title}' archived"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/categories/list", response_model=List[dict])
def list_categories(db: Session = Depends(get_document_db)):
    """
    Get list of all categories with document counts.

    Returns:
        List of categories with counts
    """
    try:
        # Query distinct categories with counts
        from sqlalchemy import func

        results = (
            db.query(Document.category, func.count(Document.id).label("count"))
            .filter(Document.is_archived == False)
            .group_by(Document.category)
            .all()
        )

        categories = [{"category": cat, "count": count} for cat, count in results]

        return categories

    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
