"""
OCR Document Digitization API

FastAPI backend for document processing with DeepSeek-OCR and Qwen.
"""

import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query, BackgroundTasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import aiofiles

from backend.config import get_settings
from backend.database import get_db, init_db, engine, Base
from backend.models import Schema, SchemaColumn, Document, OCRResult, ExtractedData, DocumentStatus
from backend.schemas import (
    SchemaCreate, SchemaResponse, SchemaListResponse, SchemaColumnCreate,
    DocumentResponse, DocumentWithDataResponse, ProcessingStatusResponse,
    HealthResponse, ModelStatus, PaginatedDocumentsResponse
)
from backend.services.ocr_service import ocr_service
from backend.services.structurizer import structurizer_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(
    title="OCR Document Digitization",
    description="API for document OCR and data extraction",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Health Check ============

@app.get("/api/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Check system health including database and AI models."""
    # Check database
    try:
        db.execute("SELECT 1")
        db_status = "online"
    except Exception:
        db_status = "offline"

    # Check models in parallel
    ocr_health, qwen_health = await asyncio.gather(
        ocr_service.check_health(),
        structurizer_service.check_health()
    )

    models = [
        ModelStatus(
            name="DeepSeek-OCR",
            url=settings.vllm_ocr_url,
            status=ocr_health.get("status", "unknown"),
            response_time=ocr_health.get("response_time")
        ),
        ModelStatus(
            name="Qwen2.5-7B",
            url=settings.vllm_qwen_url,
            status=qwen_health.get("status", "unknown"),
            response_time=qwen_health.get("response_time")
        )
    ]

    overall_status = "healthy" if db_status == "online" else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        models=models
    )


# ============ Schemas CRUD ============

@app.post("/api/schemas", response_model=SchemaResponse)
def create_schema(schema_data: SchemaCreate, db: Session = Depends(get_db)):
    """Create a new schema with columns."""
    schema = Schema(
        name=schema_data.name,
        description=schema_data.description
    )
    db.add(schema)
    db.flush()

    for i, col_data in enumerate(schema_data.columns):
        column = SchemaColumn(
            schema_id=schema.id,
            name=col_data.name,
            description=col_data.description,
            column_type=col_data.column_type,
            order=i
        )
        db.add(column)

    db.commit()
    db.refresh(schema)
    return schema


@app.get("/api/schemas", response_model=List[SchemaListResponse])
def list_schemas(db: Session = Depends(get_db)):
    """List all schemas with counts."""
    schemas = db.query(Schema).all()
    result = []
    for schema in schemas:
        columns_count = db.query(SchemaColumn).filter(SchemaColumn.schema_id == schema.id).count()
        documents_count = db.query(Document).filter(Document.schema_id == schema.id).count()
        result.append(SchemaListResponse(
            id=schema.id,
            name=schema.name,
            description=schema.description,
            columns_count=columns_count,
            documents_count=documents_count,
            created_at=schema.created_at
        ))
    return result


@app.get("/api/schemas/{schema_id}", response_model=SchemaResponse)
def get_schema(schema_id: int, db: Session = Depends(get_db)):
    """Get schema with all columns."""
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema


@app.delete("/api/schemas/{schema_id}")
def delete_schema(schema_id: int, db: Session = Depends(get_db)):
    """Delete schema and all related data."""
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    db.delete(schema)
    db.commit()
    return {"status": "deleted"}


@app.post("/api/schemas/{schema_id}/columns", response_model=SchemaResponse)
def add_column(schema_id: int, column_data: SchemaColumnCreate, db: Session = Depends(get_db)):
    """Add a column to existing schema."""
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    max_order = db.query(func.max(SchemaColumn.order)).filter(
        SchemaColumn.schema_id == schema_id
    ).scalar() or 0

    column = SchemaColumn(
        schema_id=schema_id,
        name=column_data.name,
        description=column_data.description,
        column_type=column_data.column_type,
        order=max_order + 1
    )
    db.add(column)
    db.commit()
    db.refresh(schema)
    return schema


@app.delete("/api/schemas/{schema_id}/columns/{column_id}")
def delete_column(schema_id: int, column_id: int, db: Session = Depends(get_db)):
    """Delete a column from schema."""
    column = db.query(SchemaColumn).filter(
        SchemaColumn.id == column_id,
        SchemaColumn.schema_id == schema_id
    ).first()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    db.delete(column)
    db.commit()
    return {"status": "deleted"}


# ============ Documents ============

@app.post("/api/documents/upload/{schema_id}", response_model=List[DocumentResponse])
async def upload_documents(
    schema_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload one or more documents for processing."""
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    documents = []

    for file in files:
        # Validate file type
        ext = Path(file.filename).suffix.lower().lstrip(".")
        if ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed: {settings.allowed_extensions}"
            )

        # Generate unique filename
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(settings.upload_dir, unique_name)

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            if len(content) > settings.max_file_size:
                raise HTTPException(status_code=400, detail="File too large")
            await f.write(content)

        # Create document record
        doc = Document(
            schema_id=schema_id,
            filename=unique_name,
            original_filename=file.filename,
            file_type=ext,
            file_path=file_path,
            status=DocumentStatus.PENDING
        )
        db.add(doc)
        documents.append(doc)

    db.commit()
    for doc in documents:
        db.refresh(doc)

    return documents


@app.get("/api/documents/{schema_id}", response_model=PaginatedDocumentsResponse)
def list_documents(
    schema_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List documents for a schema with pagination."""
    # Get total count
    total = db.query(Document).filter(Document.schema_id == schema_id).count()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size

    # Get paginated documents
    documents = db.query(Document).filter(
        Document.schema_id == schema_id
    ).order_by(
        Document.created_at.desc()
    ).offset(offset).limit(page_size).all()

    items = []
    for doc in documents:
        ocr_text = doc.ocr_result.raw_text if doc.ocr_result else None
        extracted = doc.extracted_data.data if doc.extracted_data else None

        items.append(DocumentWithDataResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            status=doc.status,
            error_message=doc.error_message,
            ocr_text=ocr_text,
            extracted_data=extracted,
            created_at=doc.created_at
        ))

    return PaginatedDocumentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"status": "deleted"}


# ============ Processing ============

async def process_document_task(document_id: int, db: Session):
    """Background task to process a single document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        logger.warning(f"Document {document_id} not found")
        return

    logger.info(f"Starting processing document {document_id}: {doc.original_filename}")

    schema = db.query(Schema).filter(Schema.id == doc.schema_id).first()
    columns = [{"name": c.name, "description": c.description} for c in schema.columns]

    try:
        # Step 1: OCR
        doc.status = DocumentStatus.OCR_PROCESSING
        db.commit()
        logger.info(f"Document {document_id}: Starting OCR")

        ocr_result = await ocr_service.process_image(doc.file_path)
        logger.info(f"Document {document_id}: OCR completed in {ocr_result['processing_time']}ms")

        ocr_record = OCRResult(
            document_id=doc.id,
            raw_text=ocr_result["text"],
            processing_time=ocr_result["processing_time"]
        )
        db.add(ocr_record)
        doc.status = DocumentStatus.OCR_DONE
        db.commit()

        # Step 2: Structuring
        doc.status = DocumentStatus.STRUCTURING
        db.commit()
        logger.info(f"Document {document_id}: Starting structuring")

        struct_result = await structurizer_service.structure_data(
            ocr_result["text"],
            columns
        )
        logger.info(f"Document {document_id}: Structuring completed in {struct_result['processing_time']}ms, confidence: {struct_result['confidence']}%")

        extracted = ExtractedData(
            document_id=doc.id,
            data=struct_result["data"],
            confidence=struct_result["confidence"],
            processing_time=struct_result["processing_time"]
        )
        db.add(extracted)
        doc.status = DocumentStatus.COMPLETED
        db.commit()
        logger.info(f"Document {document_id}: Processing completed successfully")

    except Exception as e:
        logger.error(f"Document {document_id}: Processing failed - {str(e)}")
        doc.status = DocumentStatus.ERROR
        doc.error_message = str(e)
        db.commit()


@app.post("/api/process/{document_id}")
async def process_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start processing a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status not in [DocumentStatus.PENDING, DocumentStatus.ERROR]:
        raise HTTPException(status_code=400, detail="Document already processing or completed")

    background_tasks.add_task(process_document_task, document_id, db)

    return {"status": "processing_started", "document_id": document_id}


@app.post("/api/process/batch/{schema_id}")
async def process_batch(
    schema_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process all pending documents in a schema."""
    documents = db.query(Document).filter(
        Document.schema_id == schema_id,
        Document.status.in_([DocumentStatus.PENDING, DocumentStatus.ERROR])
    ).all()

    for doc in documents:
        background_tasks.add_task(process_document_task, doc.id, db)

    return {"status": "batch_started", "count": len(documents)}


@app.get("/api/process/stream/{schema_id}")
async def process_stream(schema_id: int, db: Session = Depends(get_db)):
    """SSE endpoint for real-time processing updates."""
    # Validate schema exists
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    async def event_generator():
        last_states = {}

        while True:
            documents = db.query(Document).filter(Document.schema_id == schema_id).all()

            for doc in documents:
                current_state = {
                    "id": doc.id,
                    "status": doc.status.value,
                    "error": doc.error_message
                }

                # Check if state changed
                if last_states.get(doc.id) != current_state:
                    last_states[doc.id] = current_state

                    # Get extracted data if available
                    extracted = None
                    if doc.extracted_data:
                        extracted = doc.extracted_data.data

                    ocr_text = None
                    if doc.ocr_result:
                        ocr_text = doc.ocr_result.raw_text[:500]  # First 500 chars

                    progress = {
                        DocumentStatus.PENDING.value: 0,
                        DocumentStatus.OCR_PROCESSING.value: 25,
                        DocumentStatus.OCR_DONE.value: 50,
                        DocumentStatus.STRUCTURING.value: 75,
                        DocumentStatus.COMPLETED.value: 100,
                        DocumentStatus.ERROR.value: 0
                    }.get(doc.status.value, 0)

                    data = ProcessingStatusResponse(
                        document_id=doc.id,
                        status=doc.status,
                        progress=progress,
                        message=f"Processing: {doc.status.value}",
                        ocr_text=ocr_text,
                        extracted_data=extracted
                    )

                    yield f"data: {data.model_dump_json()}\n\n"

            # Check if all done
            all_done = all(
                doc.status in [DocumentStatus.COMPLETED, DocumentStatus.ERROR]
                for doc in documents
            ) if documents else True

            if all_done and documents:
                yield f"data: {{'event': 'complete'}}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============ Static Files & Frontend ============

# Serve uploaded files
@app.get("/uploads/{filename}")
async def get_upload(filename: str):
    """Serve uploaded files."""
    file_path = os.path.join(settings.upload_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


# Mount frontend
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend."""
    with open("frontend/index.html", "r") as f:
        return f.read()
