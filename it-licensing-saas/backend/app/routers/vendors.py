from __future__ import annotations
import csv
from io import StringIO
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ..database import get_session
from ..auth import require_api_key
from .. import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.VendorOut)
def create_vendor(payload: schemas.VendorCreate, db: Session = Depends(get_session), org=Depends(require_api_key)):
    existing = db.query(models.Vendor).filter(models.Vendor.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Vendor already exists")
    vendor = models.Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/", response_model=list[schemas.VendorOut])
def list_vendors(db: Session = Depends(get_session), org=Depends(require_api_key)):
    return db.query(models.Vendor).order_by(models.Vendor.name).all()


@router.post("/import-fiscal-csv", response_model=schemas.ImportResult)
async def import_fiscal_csv(file: UploadFile = File(...), db: Session = Depends(get_session), org=Depends(require_api_key)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    text = (await file.read()).decode("utf-8")
    reader = csv.DictReader(StringIO(text))
    required = {"vendor_name", "fye_month", "fye_day"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(sorted(missing))}")

    created = 0
    updated = 0
    errors: list[str] = []

    for idx, row in enumerate(reader, start=2):
        name = (row.get("vendor_name") or "").strip()
        try:
            fye_month = int(row.get("fye_month") or 0) or None
            fye_day = int(row.get("fye_day") or 0) or None
        except ValueError:
            errors.append(f"Row {idx}: invalid month/day")
            continue
        if not name:
            errors.append(f"Row {idx}: vendor_name is required")
            continue

        vendor = db.query(models.Vendor).filter(models.Vendor.name == name).first()
        if vendor:
            vendor.fye_month = fye_month
            vendor.fye_day = fye_day
            updated += 1
        else:
            vendor = models.Vendor(name=name, fye_month=fye_month, fye_day=fye_day)
            db.add(vendor)
            created += 1

    db.commit()
    return schemas.ImportResult(created=created, updated=updated, errors=errors)