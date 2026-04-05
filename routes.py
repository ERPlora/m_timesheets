"""
Timesheets module HTMX views — FastAPI router.

Replaces Django views.py + urls.py. Uses @htmx_view decorator.
Mounted at /m/timesheets/ by ModuleRuntime.
"""

from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.db.query import HubQuery
from app.core.db.transactions import atomic
from app.core.dependencies import CurrentUser, DbSession, HubId
from app.core.htmx import htmx_view

from .models import (
    HourlyRate,
    TimeEntry,
    TimesheetApproval,
    TimesheetsSettings,
)
from .schemas import (
    ApprovalAction,
    HourlyRateCreate,
    HourlyRateUpdate,
    TimeEntryCreate,
    TimeEntryUpdate,
    TimesheetsSettingsUpdate,
)

router = APIRouter()


def _q(model, db, hub_id):
    return HubQuery(model, db, hub_id)


def _week_bounds(ref_date: datetime.date | None = None):
    """Return (monday, sunday) for the week containing ref_date."""
    if ref_date is None:
        ref_date = datetime.date.today()
    monday = ref_date - datetime.timedelta(days=ref_date.weekday())
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


# ============================================================================
# My Time (index) — weekly view
# ============================================================================

@router.get("/")
@htmx_view(module_id="timesheets", view_id="my_time")
async def my_time(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
    week: int = 0,
):
    """Weekly time entry view for the current user."""
    today = datetime.date.today()
    ref_date = today + datetime.timedelta(weeks=week)
    monday, sunday = _week_bounds(ref_date)

    entries = await (
        _q(TimeEntry, db, hub_id)
        .filter(
            TimeEntry.employee_id == user.id,
            TimeEntry.date >= monday,
            TimeEntry.date <= sunday,
        )
        .order_by(TimeEntry.date, TimeEntry.start_time)
        .all()
    )

    # Build day-by-day structure
    days = []
    for i in range(7):
        day_date = monday + datetime.timedelta(days=i)
        day_entries = [e for e in entries if e.date == day_date]
        day_total = sum(e.duration_minutes for e in day_entries)
        days.append({
            "date": day_date,
            "entries": day_entries,
            "total_minutes": day_total,
            "total_hours": round(day_total / 60, 1) if day_total else 0,
            "is_today": day_date == today,
        })

    total_minutes = sum(d["total_minutes"] for d in days)
    billable_entries = [e for e in entries if e.billable]
    billable_minutes = sum(e.duration_minutes for e in billable_entries)

    # Get active hourly rates for the add form
    rates = await (
        _q(HourlyRate, db, hub_id)
        .filter(HourlyRate.is_active == True)  # noqa: E712
        .order_by(HourlyRate.name)
        .all()
    )

    # Get settings for default values
    settings = await _q(TimesheetsSettings, db, hub_id).first()

    return {
        "days": days,
        "monday": monday,
        "sunday": sunday,
        "week_offset": week,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1) if total_minutes else 0,
        "billable_minutes": billable_minutes,
        "billable_hours": round(billable_minutes / 60, 1) if billable_minutes else 0,
        "entries_count": len(entries),
        "rates": rates,
        "settings": settings,
    }


# ============================================================================
# Time Entry CRUD
# ============================================================================

@router.post("/entries/add")
async def entry_add(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Create a new time entry."""
    try:
        body = await request.json()
        data = TimeEntryCreate(**body)

        # Resolve hourly rate
        rate_amount = None
        if data.hourly_rate_id:
            rate = await _q(HourlyRate, db, hub_id).get(data.hourly_rate_id)
            if rate:
                rate_amount = rate.rate

        # Get employee name
        employee_name = getattr(user, "name", "") or getattr(user, "display_name", "")

        # Get settings for default billable
        if "billable" not in body:
            settings = await _q(TimesheetsSettings, db, hub_id).first()
            if settings:
                data.billable = settings.default_billable

        async with atomic(db) as session:
            entry = TimeEntry(
                hub_id=hub_id,
                employee_id=user.id,
                employee_name=employee_name,
                date=data.date,
                start_time=data.start_time,
                end_time=data.end_time,
                duration_minutes=data.duration_minutes,
                description=data.description,
                billable=data.billable,
                project_name=data.project_name,
                client_name=data.client_name,
                hourly_rate_id=data.hourly_rate_id,
                rate_amount=rate_amount,
            )
            session.add(entry)

        return JSONResponse({"success": True, "id": str(entry.id)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.post("/entries/{entry_id}/edit")
async def entry_edit(
    request: Request, entry_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Edit an existing time entry."""
    entry = await _q(TimeEntry, db, hub_id).get(entry_id)
    if entry is None:
        return JSONResponse({"success": False, "error": "Time entry not found"}, status_code=404)

    if entry.status not in ("draft", "rejected"):
        return JSONResponse({"success": False, "error": "Only draft or rejected entries can be edited"})

    try:
        body = await request.json()
        data = TimeEntryUpdate(**body)

        for key, value in data.model_dump(exclude_unset=True).items():
            if key == "hourly_rate_id" and value is not None:
                rate = await _q(HourlyRate, db, hub_id).get(value)
                if rate:
                    entry.rate_amount = rate.rate
            setattr(entry, key, value)

        await db.flush()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.post("/entries/{entry_id}/delete")
async def entry_delete(
    request: Request, entry_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Soft-delete a time entry."""
    deleted = await _q(TimeEntry, db, hub_id).delete(entry_id)
    if not deleted:
        return JSONResponse({"success": False, "error": "Time entry not found"}, status_code=404)
    return JSONResponse({"success": True})


@router.post("/entries/{entry_id}/submit")
async def entry_submit(
    request: Request, entry_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Submit a draft time entry for approval."""
    entry = await _q(TimeEntry, db, hub_id).get(entry_id)
    if entry is None:
        return JSONResponse({"success": False, "error": "Time entry not found"}, status_code=404)

    if entry.status != "draft":
        return JSONResponse({"success": False, "error": "Only draft entries can be submitted"})

    entry.status = "submitted"
    await db.flush()
    return JSONResponse({"success": True})


# ============================================================================
# Approvals
# ============================================================================

@router.get("/approvals")
@htmx_view(module_id="timesheets", view_id="approvals")
async def approvals_view(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """List submitted time entries pending approval."""
    submitted_entries = await (
        _q(TimeEntry, db, hub_id)
        .filter(TimeEntry.status == "submitted")
        .order_by(TimeEntry.employee_name, TimeEntry.date)
        .all()
    )

    pending_approvals = await (
        _q(TimesheetApproval, db, hub_id)
        .filter(TimesheetApproval.status == "pending")
        .order_by(TimesheetApproval.period_start.desc())
        .all()
    )

    return {
        "submitted_entries": submitted_entries,
        "pending_approvals": pending_approvals,
    }


@router.post("/approvals/{entry_id}/approve")
async def approval_approve(
    request: Request, entry_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Approve a submitted time entry."""
    entry = await _q(TimeEntry, db, hub_id).get(entry_id)
    if entry is None:
        return JSONResponse({"success": False, "error": "Time entry not found"}, status_code=404)

    if entry.status != "submitted":
        return JSONResponse({"success": False, "error": "Only submitted entries can be approved"})

    entry.status = "approved"
    await db.flush()
    return JSONResponse({"success": True})


@router.post("/approvals/{entry_id}/reject")
async def approval_reject(
    request: Request, entry_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Reject a submitted time entry."""
    entry = await _q(TimeEntry, db, hub_id).get(entry_id)
    if entry is None:
        return JSONResponse({"success": False, "error": "Time entry not found"}, status_code=404)

    if entry.status != "submitted":
        return JSONResponse({"success": False, "error": "Only submitted entries can be rejected"})

    try:
        body = await request.json()
        ApprovalAction(**body)
    except Exception:
        pass

    entry.status = "rejected"
    await db.flush()
    return JSONResponse({"success": True})


# ============================================================================
# Reports
# ============================================================================

@router.get("/reports")
@htmx_view(module_id="timesheets", view_id="reports")
async def reports_view(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
    date_from: str = "", date_to: str = "", employee: str = "",
):
    """Reports page with date/employee filters."""
    query = _q(TimeEntry, db, hub_id)

    if date_from:
        query = query.filter(TimeEntry.date >= date_from)
    else:
        # Default: current month
        today = datetime.date.today()
        date_from = today.replace(day=1).isoformat()
        query = query.filter(TimeEntry.date >= date_from)

    if date_to:
        query = query.filter(TimeEntry.date <= date_to)

    if employee:
        query = query.filter(TimeEntry.employee_id == uuid.UUID(employee))

    all_entries = await query.order_by(TimeEntry.date).all()

    # Summaries
    total_minutes = sum(e.duration_minutes for e in all_entries)
    billable_entries = [e for e in all_entries if e.billable]
    billable_minutes = sum(e.duration_minutes for e in billable_entries)
    non_billable_minutes = total_minutes - billable_minutes

    # By employee
    by_employee: dict[str, dict] = {}
    for e in all_entries:
        eid = str(e.employee_id)
        if eid not in by_employee:
            by_employee[eid] = {
                "employee_id": eid,
                "employee_name": e.employee_name or eid,
                "total_minutes": 0,
                "billable_minutes": 0,
            }
        by_employee[eid]["total_minutes"] += e.duration_minutes
        if e.billable:
            by_employee[eid]["billable_minutes"] += e.duration_minutes

    for emp in by_employee.values():
        emp["total_hours"] = round(emp["total_minutes"] / 60, 1)
        emp["billable_hours"] = round(emp["billable_minutes"] / 60, 1)

    # By project
    by_project: dict[str, dict] = {}
    for e in all_entries:
        pname = e.project_name or ""
        if not pname:
            continue
        if pname not in by_project:
            by_project[pname] = {
                "project_name": pname,
                "total_minutes": 0,
                "billable_minutes": 0,
            }
        by_project[pname]["total_minutes"] += e.duration_minutes
        if e.billable:
            by_project[pname]["billable_minutes"] += e.duration_minutes

    for proj in by_project.values():
        proj["total_hours"] = round(proj["total_minutes"] / 60, 1)
        proj["billable_hours"] = round(proj["billable_minutes"] / 60, 1)

    return {
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1) if total_minutes else 0,
        "billable_minutes": billable_minutes,
        "billable_hours": round(billable_minutes / 60, 1) if billable_minutes else 0,
        "non_billable_minutes": non_billable_minutes,
        "non_billable_hours": round(non_billable_minutes / 60, 1) if non_billable_minutes else 0,
        "by_employee": list(by_employee.values()),
        "by_project": list(by_project.values()),
        "date_from": date_from,
        "date_to": date_to,
        "filter_employee": employee,
    }


# ============================================================================
# Rates
# ============================================================================

@router.get("/rates")
@htmx_view(module_id="timesheets", view_id="rates")
async def rates_view(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Hourly rates list."""
    rates = await (
        _q(HourlyRate, db, hub_id)
        .order_by(HourlyRate.name)
        .all()
    )
    return {"rates": rates}


@router.post("/rates/add")
async def rate_add(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Create a new hourly rate."""
    try:
        body = await request.json()
        data = HourlyRateCreate(**body)

        async with atomic(db) as session:
            rate = HourlyRate(hub_id=hub_id, **data.model_dump())
            session.add(rate)

        return JSONResponse({"success": True, "id": str(rate.id)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.post("/rates/{rate_id}/edit")
async def rate_edit(
    request: Request, rate_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Edit an existing hourly rate."""
    rate = await _q(HourlyRate, db, hub_id).get(rate_id)
    if rate is None:
        return JSONResponse({"success": False, "error": "Rate not found"}, status_code=404)

    try:
        body = await request.json()
        data = HourlyRateUpdate(**body)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(rate, key, value)
        await db.flush()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.post("/rates/{rate_id}/delete")
async def rate_delete(
    request: Request, rate_id: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Soft-delete an hourly rate."""
    deleted = await _q(HourlyRate, db, hub_id).delete(rate_id)
    if not deleted:
        return JSONResponse({"success": False, "error": "Rate not found"}, status_code=404)
    return JSONResponse({"success": True})


# ============================================================================
# Settings
# ============================================================================

@router.get("/settings")
@htmx_view(module_id="timesheets", view_id="settings")
async def settings_view(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Timesheets settings page."""
    settings = await _q(TimesheetsSettings, db, hub_id).first()
    if settings is None:
        async with atomic(db) as session:
            settings = TimesheetsSettings(hub_id=hub_id)
            session.add(settings)
            await session.flush()

    return {"settings": settings}


@router.post("/settings/save")
async def settings_save(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Save timesheets settings."""
    try:
        body = await request.json()
        data = TimesheetsSettingsUpdate(**body)

        settings = await _q(TimesheetsSettings, db, hub_id).first()
        if settings is None:
            async with atomic(db) as session:
                settings = TimesheetsSettings(hub_id=hub_id)
                session.add(settings)
                await session.flush()

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(settings, key, value)
        await db.flush()

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
