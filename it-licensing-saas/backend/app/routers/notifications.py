from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_session
from ..auth import require_api_key
from .. import models

router = APIRouter()


@router.get("/")
def list_notifications(db: Session = Depends(get_session), org=Depends(require_api_key)):
    return (
        db.query(models.Notification)
        .filter(models.Notification.organization_id == org.id)
        .order_by(models.Notification.created_at.desc())
        .limit(200)
        .all()
    )


@router.post("/")
def create_notification(payload: dict, db: Session = Depends(get_session), org=Depends(require_api_key)):
    notif = models.Notification(
        organization_id=org.id,
        license_id=payload.get("license_id"),
        type=payload.get("type", "info"),
        message=payload.get("message", ""),
        status="pending",
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif