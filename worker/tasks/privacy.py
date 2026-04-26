"""
Privacy / data-retention purge task.

Runs daily via celery beat.  Two responsibilities:

1. Hard-delete records that were soft-deleted long enough ago
   (DELETE blueprint_jobs / uploaded_documents older than
   ``soft_delete_grace_days``).

2. Soft-delete records whose retention window has fully expired
   (older than ``data_retention_days`` since creation) so the next pass
   hard-deletes them.

In both cases the underlying object-storage blob is removed first, and
DB rows are removed last.  Errors are logged but never crash the task.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from worker.worker import app

logger = structlog.get_logger()


def _sync_db_url() -> str:
    import os
    url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL", "")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url


@app.task(name="worker.tasks.privacy.purge_expired_uploads", bind=True)
def purge_expired_uploads(self) -> dict:
    """Hard-delete soft-deleted records and soft-delete retention-expired ones."""
    # Imports kept inside the task so celery worker startup stays light.
    from app.config import settings
    from app.core.storage import storage_client
    from app.models.blueprints import BlueprintJob, BlueprintPage
    from app.models.documents import UploadedDocument, DocumentChunk

    engine = create_engine(_sync_db_url(), future=True)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    now = datetime.now(timezone.utc)
    grace_cutoff = now - timedelta(days=settings.soft_delete_grace_days)
    retention_cutoff = now - timedelta(days=settings.data_retention_days)

    stats = {
        "blueprint_hard_deleted": 0,
        "blueprint_soft_deleted": 0,
        "document_hard_deleted": 0,
        "document_soft_deleted": 0,
        "blob_delete_errors": 0,
    }

    with Session() as session:
        # 1. BlueprintJob — hard-delete past grace window
        rows = session.execute(
            select(BlueprintJob).where(
                BlueprintJob.deleted_at.is_not(None),
                BlueprintJob.deleted_at <= grace_cutoff,
            )
        ).scalars().all()
        for job in rows:
            try:
                if job.storage_path:
                    ok = storage_client.delete_file(
                        settings.minio_bucket_blueprints, job.storage_path
                    )
                    if not ok:
                        stats["blob_delete_errors"] += 1
                # Cascade-delete pages (no FK ON DELETE CASCADE configured)
                session.execute(
                    BlueprintPage.__table__.delete().where(BlueprintPage.job_id == job.id)
                )
                session.delete(job)
                stats["blueprint_hard_deleted"] += 1
            except Exception as e:
                logger.error("privacy.purge.blueprint_hard_delete_failed",
                             job_id=job.id, error=str(e))
        session.commit()

        # 2. BlueprintJob — soft-delete past retention window
        rows = session.execute(
            select(BlueprintJob).where(
                BlueprintJob.deleted_at.is_(None),
                BlueprintJob.created_at <= retention_cutoff,
            )
        ).scalars().all()
        for job in rows:
            try:
                if job.storage_path:
                    storage_client.delete_file(
                        settings.minio_bucket_blueprints, job.storage_path
                    )
                job.deleted_at = now
                job.status = "expired"
                stats["blueprint_soft_deleted"] += 1
            except Exception as e:
                logger.error("privacy.purge.blueprint_soft_delete_failed",
                             job_id=job.id, error=str(e))
        session.commit()

        # 3. UploadedDocument — hard-delete past grace window
        rows = session.execute(
            select(UploadedDocument).where(
                UploadedDocument.deleted_at.is_not(None),
                UploadedDocument.deleted_at <= grace_cutoff,
            )
        ).scalars().all()
        for doc in rows:
            try:
                if doc.storage_path:
                    ok = storage_client.delete_file(
                        settings.minio_bucket_documents, doc.storage_path
                    )
                    if not ok:
                        stats["blob_delete_errors"] += 1
                session.execute(
                    DocumentChunk.__table__.delete().where(DocumentChunk.document_id == doc.id)
                )
                session.delete(doc)
                stats["document_hard_deleted"] += 1
            except Exception as e:
                logger.error("privacy.purge.document_hard_delete_failed",
                             doc_id=doc.id, error=str(e))
        session.commit()

        # 4. UploadedDocument — soft-delete past retention window
        rows = session.execute(
            select(UploadedDocument).where(
                UploadedDocument.deleted_at.is_(None),
                UploadedDocument.created_at <= retention_cutoff,
            )
        ).scalars().all()
        for doc in rows:
            try:
                if doc.storage_path:
                    storage_client.delete_file(
                        settings.minio_bucket_documents, doc.storage_path
                    )
                doc.deleted_at = now
                doc.status = "expired"
                stats["document_soft_deleted"] += 1
            except Exception as e:
                logger.error("privacy.purge.document_soft_delete_failed",
                             doc_id=doc.id, error=str(e))
        session.commit()

    logger.info("privacy.purge.completed", **stats)
    return stats
