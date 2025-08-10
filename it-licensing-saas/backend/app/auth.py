from __future__ import annotations
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .database import get_session
from .models import Organization


def require_api_key(x_api_key: str | None = Header(default=None), db: Session = Depends(get_session)) -> Organization:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    org = db.query(Organization).filter(Organization.api_key == x_api_key).first()
    if not org:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return org