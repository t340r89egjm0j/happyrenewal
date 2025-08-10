from __future__ import annotations
import csv
from pathlib import Path
from sqlalchemy.orm import Session
from .. import models

SAMPLE_CSV = Path(__file__).with_name("fiscal_year_sample.csv")


def seed_sample_vendors(db: Session) -> tuple[int, int]:
    if not SAMPLE_CSV.exists():
        return (0, 0)
    created = 0
    updated = 0
    with SAMPLE_CSV.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("vendor_name") or "").strip()
            if not name:
                continue
            fye_month = int(row.get("fye_month") or 0) or None
            fye_day = int(row.get("fye_day") or 0) or None
            vendor = db.query(models.Vendor).filter(models.Vendor.name == name).first()
            if vendor:
                if vendor.fye_month != fye_month or vendor.fye_day != fye_day:
                    vendor.fye_month = fye_month
                    vendor.fye_day = fye_day
                    updated += 1
            else:
                db.add(models.Vendor(name=name, fye_month=fye_month, fye_day=fye_day))
                created += 1
    db.commit()
    return (created, updated)