from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditLog


async def log_audit_event(db: AsyncSession, user_id: str, action: str, resource: str = None):
    log_entry = AuditLog(user_id=user_id, action=action, resource=resource)
    db.add(log_entry)
    await db.commit()
