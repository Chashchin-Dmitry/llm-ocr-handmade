from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    """Status of document processing."""
    PENDING = "pending"
    OCR_PROCESSING = "ocr_processing"
    OCR_DONE = "ocr_done"
    STRUCTURING = "structuring"
    COMPLETED = "completed"
    ERROR = "error"


class Schema(Base):
    """
    User-defined schema for document extraction.
    Users create columns with descriptions for AI to understand what to extract.
    """
    __tablename__ = "schemas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    columns = relationship("SchemaColumn", back_populates="schema", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="schema")


class SchemaColumn(Base):
    """
    Column definition within a schema.
    Each column has a name and description that AI uses to extract data.
    """
    __tablename__ = "schema_columns"

    id = Column(Integer, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey("schemas.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)  # AI reads this to understand what to extract
    column_type = Column(String(50), default="text")  # text, number, date, etc.
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    schema = relationship("Schema", back_populates="columns")


class Document(Base):
    """
    Uploaded document for processing.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey("schemas.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # png, pdf, doc, etc.
    file_path = Column(String(500), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    schema = relationship("Schema", back_populates="documents")
    ocr_result = relationship("OCRResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    extracted_data = relationship("ExtractedData", back_populates="document", uselist=False, cascade="all, delete-orphan")


class OCRResult(Base):
    """
    Raw OCR output from DeepSeek-OCR.
    """
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    raw_text = Column(Text, nullable=False)
    model_used = Column(String(100), default="deepseek-ocr")
    processing_time = Column(Integer, nullable=True)  # milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="ocr_result")


class ExtractedData(Base):
    """
    Structured data extracted by Qwen based on schema columns.
    """
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    data = Column(JSON, nullable=False)  # {"column_name": "extracted_value", ...}
    model_used = Column(String(100), default="qwen2.5-7b")
    processing_time = Column(Integer, nullable=True)  # milliseconds
    confidence = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="extracted_data")
