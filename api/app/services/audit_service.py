"""Audit Service — Log all estimate create/update operations."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
import structlog

logger = structlog.get_logger()


class AuditService:

    async def log(
        self,
        db: AsyncSession,
        table_name: str,
        action: str,
        record_id: Optional[int] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        try:
            entry = AuditLog(
                table_name=table_name,
                record_id=record_id,
                action=action,
                old_values=old_values,
                new_values=new_values,
                user_id=user_id,
                ip_address=ip_address,
            )
            db.add(entry)
            await db.flush()
            logger.info("Audit logged", table=table_name, action=action, record_id=record_id)
        except Exception as e:
            logger.error("Audit log failed", error=str(e))


audit_service = AuditService()
