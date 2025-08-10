from __future__ import annotations
from datetime import date, timedelta
from typing import Iterable
from ..models import Vendor, License


def _last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    first_next = date(year, month + 1, 1)
    return first_next - timedelta(days=1)


def get_vendor_quarter_end_dates(today: date, fye_month: int | None, fye_day: int | None) -> list[date]:
    if not fye_month or not fye_day:
        # Default to calendar quarters
        base_year = today.year
        quarters = [(3, 31), (6, 30), (9, 30), (12, 31)]
        return [date(base_year if today <= date(base_year, m, d) else base_year + 1, m, d) for m, d in quarters]

    # Build fiscal year end for the current or next year
    base_year = today.year
    fye_this_year = date(base_year, fye_month, min(fye_day, _last_day_of_month(base_year, fye_month).day))
    if today > fye_this_year:
        base_year += 1
        fye_this_year = date(base_year, fye_month, min(fye_day, _last_day_of_month(base_year, fye_month).day))

    # Quarter ends are spaced 3 months apart backwards from FYE
    months = []
    m = fye_month
    for _ in range(4):
        months.append(m)
        m = 12 if m - 3 <= 0 else m - 3
    months = list(reversed(months))

    quarter_dates: list[date] = []
    for month in months:
        # approximate same day within month, clamp to last day
        d = min(fye_day, _last_day_of_month(base_year - (1 if month > fye_month else 0), month).day)
        y = base_year - (1 if month > fye_month else 0)
        qd = date(y, month, d)
        if qd < today:
            # shift to next fiscal year cycle
            y2 = y + 1
            d2 = min(fye_day, _last_day_of_month(y2, month).day)
            qd = date(y2, month, d2)
        quarter_dates.append(qd)

    # Ensure ascending order and unique
    quarter_dates = sorted(sorted(set(quarter_dates)))
    return quarter_dates


def recommend_contact_window_for_vendor(today: date, vendor: Vendor) -> tuple[date, date, str, float]:
    quarters = get_vendor_quarter_end_dates(today, vendor.fye_month, vendor.fye_day)
    next_qe = min([qd for qd in quarters if qd >= today]) if quarters else today
    # Recommend a window in the 30 days leading to quarter end
    start = next_qe - timedelta(days=30)
    end = next_qe
    reason = (
        "Vendors often push to hit quarterly targets; engaging in the 2-4 weeks before quarter end can unlock better pricing."
    )
    # Boost confidence if approaching FYE
    is_fye = vendor.fye_month is not None and vendor.fye_day is not None and next_qe.month == vendor.fye_month
    confidence = 0.8 if is_fye else 0.7
    return start, end, reason, confidence


def recommend_for_licenses(today: date, licenses: Iterable[License]) -> list[dict]:
    output: list[dict] = []
    for lic in licenses:
        vendor = lic.vendor
        start, end, reason, confidence = recommend_contact_window_for_vendor(today, vendor)
        output.append(
            {
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "license_id": lic.id,
                "license_product": lic.product_name,
                "recommended_contact_window_start": start,
                "recommended_contact_window_end": end,
                "reason": reason,
                "confidence": confidence,
            }
        )
    return output