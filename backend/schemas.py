from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from backend.models import DocumentStatus


# ============ Schema (таблица пользователя) ============

class SchemaColumnCreate(BaseModel):
    """Create a new column in schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, description="Description for AI to understand what to extract")
    column_type: str = Field(default="text")
    order: int = Field(default=0)


class SchemaColumnResponse(BaseModel):
    """Column response."""
    id: int
    name: str
    description: str
    column_type: str
    order: int

    class Config:
        from_attributes = True


class SchemaCreate(BaseModel):
    """Create a new schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    columns: List[SchemaColumnCreate] = Field(default_factory=list)


class SchemaResponse(BaseModel):
    """Schema response."""
    id: int
    name: str
    description: Optional[str]
    columns: List[SchemaColumnResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class SchemaListResponse(BaseModel):
    """List of schemas."""
    id: int
    name: str
    description: Optional[str]
    columns_count: int
    documents_count: int
    created_at: datetime


# ============ Document ============

class DocumentResponse(BaseModel):
    """Document response."""
    id: int
    filename: str
    original_filename: str
    file_type: str
    status: DocumentStatus
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentWithDataResponse(BaseModel):
    """Document with extracted data."""
    id: int
    filename: str
    original_filename: str
    file_type: str
    status: DocumentStatus
    error_message: Optional[str]
    ocr_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Processing ============

class ProcessingStatusResponse(BaseModel):
    """Real-time processing status."""
    document_id: int
    status: DocumentStatus
    progress: int  # 0-100
    message: str
    ocr_text: Optional[str] = None
    extracted_data: Optional[dict] = None


# ============ Health Check ============

class ModelStatus(BaseModel):
    """Status of a model."""
    name: str
    url: str
    status: str  # online, offline, loading
    response_time: Optional[int] = None  # ms


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    models: List[ModelStatus]
