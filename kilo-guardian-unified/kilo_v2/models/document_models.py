"""
Document Models - Database schema for general document storage and search.

Stores scanned documents with:
- PDF file (local filesystem)
- OCR text (searchable)
- Tags and categories
- Voice search support
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from kilo_v2.models.auth_models import Base


class Document(Base):
    """
    Scanned document with OCR text for search.

    Documents are stored locally:
    - PDF file saved to kilo_data/documents/
    - OCR text in database for fast search
    - Tags for categorization
    - Voice search via keyword matching
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)  # User-provided or auto-generated
    category = Column(
        String(100), nullable=False
    )  # 'medical', 'bills', 'letters', 'pt_exercises', etc.
    tags = Column(
        Text
    )  # Comma-separated tags: "physical therapy, knee exercises, doctor smith"

    # OCR and content
    ocr_text = Column(Text, nullable=False)  # Full OCR text for search
    ocr_confidence = Column(Integer)  # OCR confidence score (0-100)

    # File storage
    pdf_path = Column(
        String(1000), nullable=False
    )  # Relative path: documents/2025/12/doc_123.pdf
    original_filename = Column(String(500))  # Original uploaded filename
    file_size = Column(Integer)  # File size in bytes

    # Metadata
    scan_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Flags
    is_favorite = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Document {self.id}: {self.title} ({self.category})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "tags": self.tags.split(",") if self.tags else [],
            "ocr_text": (
                self.ocr_text[:200] + "..."
                if len(self.ocr_text) > 200
                else self.ocr_text
            ),
            "ocr_confidence": self.ocr_confidence,
            "pdf_path": self.pdf_path,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "scan_date": self.scan_date.isoformat() if self.scan_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_favorite": self.is_favorite,
            "is_archived": self.is_archived,
        }
