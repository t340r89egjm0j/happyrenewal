from __future__ import annotations
import secrets
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_session
from .. import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.OrganizationOut)
def create_org(payload: schemas.OrganizationCreate, db: Session = Depends(get_session)):
    api_key = secrets.token_hex(24)
    org = models.Organization(name=payload.name, domain=payload.domain, api_key=api_key)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/", response_model=list[schemas.OrganizationOut])
def list_orgs(db: Session = Depends(get_session)):
    return db.query(models.Organization).order_by(models.Organization.created_at.desc()).all()