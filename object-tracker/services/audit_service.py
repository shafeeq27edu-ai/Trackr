from sqlalchemy.orm import Session
from db.models import AuditLog

def log_audit_event(db: Session, user_id: str, action: str, resource: str = None):
    log_entry = AuditLog(user_id=user_id, action=action, resource=resource)
    db.add(log_entry)
    db.commit()
