from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class OrganizationCreate(BaseModel):
    name: str
    domain: Optional[str] = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    domain: Optional[str]
    api_key: str

    model_config = {
        "from_attributes": True
    }


class VendorCreate(BaseModel):
    name: str
    website: Optional[str] = None
    primary_domain: Optional[str] = None
    fye_month: Optional[int] = Field(default=None, ge=1, le=12)
    fye_day: Optional[int] = Field(default=None, ge=1, le=31)
    notes: Optional[str] = None


class VendorOut(BaseModel):
    id: int
    name: str
    website: Optional[str]
    primary_domain: Optional[str]
    fye_month: Optional[int]
    fye_day: Optional[int]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class LicenseCreate(BaseModel):
    vendor_id: int
    product_name: str
    seats: Optional[int] = None
    annual_cost: Optional[float] = None
    currency: str = "USD"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    billing_frequency: Optional[str] = None
    auto_renew: bool = True
    owner_user_id: Optional[int] = None
    notes: Optional[str] = None


class LicenseOut(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    product_name: str
    seats: Optional[int]
    annual_cost: Optional[float]
    currency: str
    start_date: Optional[date]
    end_date: Optional[date]
    billing_frequency: Optional[str]
    auto_renew: bool
    owner_user_id: Optional[int]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    vendor_id: int
    vendor_name: str
    license_id: Optional[int]
    license_product: Optional[str]
    recommended_contact_window_start: date
    recommended_contact_window_end: date
    reason: str
    confidence: float = 0.7


class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str] = []