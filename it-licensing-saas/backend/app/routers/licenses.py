from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_session
from ..auth import require_api_key
from .. import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.LicenseOut)
def create_license(payload: schemas.LicenseCreate, db: Session = Depends(get_session), org=Depends(require_api_key)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == payload.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    license_obj = models.License(
        organization_id=org.id,
        vendor_id=payload.vendor_id,
        product_name=payload.product_name,
        seats=payload.seats,
        annual_cost=payload.annual_cost,
        currency=payload.currency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        billing_frequency=payload.billing_frequency,
        auto_renew=payload.auto_renew,
        owner_user_id=payload.owner_user_id,
        notes=payload.notes,
    )
    db.add(license_obj)
    db.commit()
    db.refresh(license_obj)
    return license_obj


@router.get("/", response_model=list[schemas.LicenseOut])
def list_licenses(db: Session = Depends(get_session), org=Depends(require_api_key)):
    return (
        db.query(models.License)
        .filter(models.License.organization_id == org.id)
        .order_by(models.License.end_date.asc().nulls_last())
        .all()
    )


@router.get("/{license_id}", response_model=schemas.LicenseOut)
def get_license(license_id: int, db: Session = Depends(get_session), org=Depends(require_api_key)):
    lic = (
        db.query(models.License)
        .filter(models.License.id == license_id, models.License.organization_id == org.id)
        .first()
    )
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    return lic


@router.delete("/{license_id}")
def delete_license(license_id: int, db: Session = Depends(get_session), org=Depends(require_api_key)):
    lic = (
        db.query(models.License)
        .filter(models.License.id == license_id, models.License.organization_id == org.id)
        .first()
    )
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    db.delete(lic)
    db.commit()
    return {"ok": True}