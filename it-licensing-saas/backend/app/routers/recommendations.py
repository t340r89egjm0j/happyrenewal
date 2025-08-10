from __future__ import annotations
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_session
from ..auth import require_api_key
from .. import models, schemas
from ..services.recommendation_engine import recommend_for_licenses

router = APIRouter()


@router.get("/upcoming", response_model=list[schemas.RecommendationOut])
def get_upcoming(days: int = Query(default=180, ge=7, le=365), db: Session = Depends(get_session), org=Depends(require_api_key)):
    today = date.today()
    horizon = today + timedelta(days=days)
    licenses = (
        db.query(models.License)
        .join(models.Vendor, models.License.vendor)
        .filter(models.License.organization_id == org.id)
        .all()
    )
    recs = recommend_for_licenses(today, licenses)
    filtered = []
    for r in recs:
        if r["recommended_contact_window_start"] <= horizon:
            filtered.append(r)
    return filtered


@router.post("/generate-notifications")
def generate_notifications(days: int = Query(default=90, ge=7, le=365), db: Session = Depends(get_session), org=Depends(require_api_key)):
    today = date.today()
    horizon = today + timedelta(days=days)
    licenses = (
        db.query(models.License)
        .join(models.Vendor, models.License.vendor)
        .filter(models.License.organization_id == org.id)
        .all()
    )
    recs = recommend_for_licenses(today, licenses)
    created = 0
    for r in recs:
        if r["recommended_contact_window_start"] <= horizon:
            msg = (
                f"Plan outreach to {r['vendor_name']} for {r.get('license_product') or 'portfolio'} between "
                f"{r['recommended_contact_window_start']} and {r['recommended_contact_window_end']}."
            )
            notif = models.Notification(
                organization_id=org.id,
                license_id=r.get("license_id"),
                type="recommendation",
                message=msg,
                status="pending",
            )
            db.add(notif)
            created += 1
    db.commit()
    return {"created": created}