from sqlalchemy.orm import Session
from fastapi import Request
import models


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def log_security_event(
    db: Session,
    event_type: str,
    emis_id: str = None,
    ip_address: str = None,
    details: str = None,
) -> None:
    try:
        entry = models.SecurityLog(
            event_type=event_type,
            emis_id=emis_id,
            ip_address=ip_address,
            details=details,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
