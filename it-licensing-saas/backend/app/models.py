from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list[User]] = relationship("User", back_populates="organization")
    licenses: Mapped[list[License]] = relationship("License", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship("Organization", back_populates="users")


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    primary_domain: Mapped[str | None] = mapped_column(String(255))
    fye_month: Mapped[int | None] = mapped_column(Integer)  # 1-12
    fye_day: Mapped[int | None] = mapped_column(Integer)    # 1-31
    notes: Mapped[str | None] = mapped_column(Text)

    licenses: Mapped[list[License]] = relationship("License", back_populates="vendor")


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)

    product_name: Mapped[str] = mapped_column(String(255))
    seats: Mapped[int | None] = mapped_column(Integer)
    annual_cost: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    billing_frequency: Mapped[str | None] = mapped_column(String(50))  # annual, monthly, etc
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship("Organization", back_populates="licenses")
    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="licenses")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    license_id: Mapped[int | None] = mapped_column(ForeignKey("licenses.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/sent/error
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)