from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    doc_type = Column(String(100), nullable=False)  # price_sheet, spec, code, manual
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    storage_path = Column(String(1000), nullable=True)  # MinIO path
    status = Column(String(50), default="pending")  # pending, processing, complete, error
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    processing_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Privacy / retention
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    retention_until = Column(DateTime(timezone=True), nullable=True, index=True)

    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("uploaded_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # embedding vector stored as JSON for now (pgvector extension adds proper vector column)
    embedding_json = Column(JSON, nullable=True)
    embedding = Column(Vector(1024), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("UploadedDocument", back_populates="chunks")
