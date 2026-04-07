"""
AI tools for the Timesheets module.

Uses @register_tool + AssistantTool class pattern.
All tools are async and use HubQuery for DB access.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Any

from app.ai.registry import AssistantTool, register_tool
from app.core.db.query import HubQuery
from app.core.db.transactions import atomic

from .models import HourlyRate, TimeEntry, TimesheetsSettings


def _q(model, session, hub_id):
    return HubQuery(model, session, hub_id)


@register_tool
class ListTimeEntries(AssistantTool):
    name = "list_time_entries"
    description = (
        "List time entries with optional filters by employee, date, status, project. "
        "Read-only -- no side effects."
    )
    module_id = "timesheets"
    required_permission = "timesheets.view_time_entry"
    parameters = {
        "type": "object",
        "properties": {
            "employee_id": {"type": "string", "description": "Filter by employee UUID"},
            "status": {"type": "string", "description": "Filter: draft, submitted, approved, rejected"},
            "date_from": {"type": "string", "description": "Start date filter (YYYY-MM-DD)"},
            "date_to": {"type": "string", "description": "End date filter (YYYY-MM-DD)"},
            "project_name": {"type": "string", "description": "Filter by project name (partial match)"},
            "billable": {"type": "boolean", "description": "Filter by billable flag"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id
        query = _q(TimeEntry, db, hub_id)

        if args.get("employee_id"):
            query = query.filter(TimeEntry.employee_id == uuid.UUID(args["employee_id"]))
        if args.get("status"):
            query = query.filter(TimeEntry.status == args["status"])
        if args.get("date_from"):
            d = datetime.strptime(args["date_from"], "%Y-%m-%d").date()
            query = query.filter(TimeEntry.date >= d)
        if args.get("date_to"):
            d = datetime.strptime(args["date_to"], "%Y-%m-%d").date()
            query = query.filter(TimeEntry.date <= d)
        if args.get("project_name"):
            query = query.filter(TimeEntry.project_name.ilike(f"%{args['project_name']}%"))
        if args.get("billable") is not None:
            query = query.filter(TimeEntry.billable == args["billable"])

        limit = args.get("limit", 20)
        total = await query.count()
        entries = await query.order_by(TimeEntry.date.desc()).limit(limit).all()

        return {
            "entries": [{
                "id": str(e.id),
                "employee_name": e.employee_name,
                "date": str(e.date),
                "duration_minutes": e.duration_minutes,
                "duration_hours": e.duration_hours,
                "description": e.description,
                "status": e.status,
                "billable": e.billable,
                "project_name": e.project_name,
                "client_name": e.client_name,
                "rate_amount": str(e.rate_amount) if e.rate_amount else None,
                "total_amount": str(e.total_amount) if e.total_amount else None,
            } for e in entries],
            "total": total,
        }


@register_tool
class CreateTimeEntry(AssistantTool):
    name = "create_time_entry"
    description = (
        "Create a new time entry. Duration must be positive. Cannot create entries in the future. "
        "SIDE EFFECT. Requires confirmation."
    )
    module_id = "timesheets"
    required_permission = "timesheets.add_time_entry"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "employee_id": {"type": "string", "description": "Employee UUID"},
            "employee_name": {"type": "string", "description": "Employee display name"},
            "date": {"type": "string", "description": "Entry date (YYYY-MM-DD)"},
            "duration_minutes": {"type": "integer", "description": "Duration in minutes (positive)"},
            "description": {"type": "string", "description": "Work description"},
            "project_name": {"type": "string", "description": "Project name"},
            "client_name": {"type": "string", "description": "Client name"},
            "billable": {"type": "boolean", "description": "Is billable (default true)"},
            "hourly_rate_id": {"type": "string", "description": "Hourly rate UUID"},
        },
        "required": ["employee_id", "employee_name", "date", "duration_minutes"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        entry_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
        today = date.today()

        if entry_date > today:
            return {"error": "Cannot create time entries in the future"}

        duration = args["duration_minutes"]
        if duration <= 0:
            return {"error": "Duration must be positive"}

        # Resolve rate
        rate_amount = None
        rate_id = None
        if args.get("hourly_rate_id"):
            rate_id = uuid.UUID(args["hourly_rate_id"])
            hr = await _q(HourlyRate, db, hub_id).get(rate_id)
            if hr:
                rate_amount = hr.rate

        async with atomic(db) as session:
            e = TimeEntry(
                hub_id=hub_id,
                employee_id=uuid.UUID(args["employee_id"]),
                employee_name=args["employee_name"],
                date=entry_date,
                duration_minutes=duration,
                description=args.get("description", ""),
                project_name=args.get("project_name", ""),
                client_name=args.get("client_name", ""),
                billable=args.get("billable", True),
                hourly_rate_id=rate_id,
                rate_amount=rate_amount,
                status="draft",
            )
            session.add(e)
            await session.flush()

        return {
            "id": str(e.id),
            "duration_hours": e.duration_hours,
            "total_amount": str(e.total_amount) if e.total_amount else None,
            "created": True,
        }


@register_tool
class UpdateTimeEntry(AssistantTool):
    name = "update_time_entry"
    description = (
        "Update an existing time entry. Cannot modify approved entries. "
        "SIDE EFFECT. Requires confirmation."
    )
    module_id = "timesheets"
    required_permission = "timesheets.change_time_entry"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "entry_id": {"type": "string", "description": "Time entry UUID"},
            "duration_minutes": {"type": "integer", "description": "Duration in minutes (positive)"},
            "description": {"type": "string", "description": "Work description"},
            "project_name": {"type": "string", "description": "Project name"},
            "client_name": {"type": "string", "description": "Client name"},
            "billable": {"type": "boolean", "description": "Is billable"},
        },
        "required": ["entry_id"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        e = await _q(TimeEntry, db, hub_id).get(uuid.UUID(args["entry_id"]))
        if e is None:
            return {"error": "Time entry not found"}

        if e.status == "approved":
            return {"error": "Cannot modify an approved time entry"}

        if args.get("duration_minutes") is not None and args["duration_minutes"] <= 0:
            return {"error": "Duration must be positive"}

        async with atomic(db):
            for field in ("description", "project_name", "client_name"):
                if field in args:
                    setattr(e, field, args[field])
            if "duration_minutes" in args:
                e.duration_minutes = args["duration_minutes"]
            if "billable" in args:
                e.billable = args["billable"]
            await db.flush()

        return {"id": str(e.id), "updated": True}


@register_tool
class DeleteTimeEntry(AssistantTool):
    name = "delete_time_entry"
    description = (
        "Delete a time entry. Cannot delete approved entries. "
        "SIDE EFFECT. Requires confirmation."
    )
    module_id = "timesheets"
    required_permission = "timesheets.delete_time_entry"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "entry_id": {"type": "string", "description": "Time entry UUID"},
        },
        "required": ["entry_id"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        e = await _q(TimeEntry, db, hub_id).get(uuid.UUID(args["entry_id"]))
        if e is None:
            return {"error": "Time entry not found"}

        if e.status == "approved":
            return {"error": "Cannot delete an approved time entry"}

        async with atomic(db):
            e.is_deleted = True
            e.deleted_at = datetime.now(UTC)
            await db.flush()

        return {"id": str(e.id), "deleted": True}


@register_tool
class ListHourlyRates(AssistantTool):
    name = "list_hourly_rates"
    description = "List all active hourly rates. Read-only."
    module_id = "timesheets"
    required_permission = "timesheets.view_time_entry"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        rates = await _q(HourlyRate, db, hub_id).filter(
            HourlyRate.is_active == True,  # noqa: E712
        ).order_by(HourlyRate.name).all()

        return {
            "rates": [{
                "id": str(r.id),
                "name": r.name,
                "rate": str(r.rate),
                "employee_id": str(r.employee_id) if r.employee_id else None,
                "is_default": r.is_default,
            } for r in rates],
        }


@register_tool
class CreateHourlyRate(AssistantTool):
    name = "create_hourly_rate"
    description = "Create a new hourly rate. SIDE EFFECT. Requires confirmation."
    module_id = "timesheets"
    required_permission = "timesheets.manage_rates"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Rate name"},
            "rate": {"type": "string", "description": "Rate per hour (decimal, positive)"},
            "employee_id": {"type": "string", "description": "Specific employee UUID (optional)"},
            "is_default": {"type": "boolean", "description": "Set as default rate"},
        },
        "required": ["name", "rate"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        rate_val = Decimal(args["rate"])
        if rate_val <= 0:
            return {"error": "Rate must be positive"}

        async with atomic(db) as session:
            r = HourlyRate(
                hub_id=hub_id,
                name=args["name"],
                rate=rate_val,
                employee_id=uuid.UUID(args["employee_id"]) if args.get("employee_id") else None,
                is_default=args.get("is_default", False),
            )
            session.add(r)
            await session.flush()

        return {"id": str(r.id), "name": r.name, "rate": str(r.rate), "created": True}


@register_tool
class GetTimesheetsSettings(AssistantTool):
    name = "get_timesheets_settings"
    description = "Get current timesheets settings. Read-only."
    module_id = "timesheets"
    required_permission = "timesheets.view_settings"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        settings = await _q(TimesheetsSettings, db, hub_id).first()
        if not settings:
            return {
                "default_billable": True,
                "require_approval": True,
                "approval_period": "weekly",
            }

        return {
            "default_billable": settings.default_billable,
            "require_approval": settings.require_approval,
            "approval_period": settings.approval_period,
        }


@register_tool
class UpdateTimesheetsSettings(AssistantTool):
    name = "update_timesheets_settings"
    description = "Update timesheets settings. SIDE EFFECT. Requires confirmation."
    module_id = "timesheets"
    required_permission = "timesheets.change_settings"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "default_billable": {"type": "boolean", "description": "New entries are billable by default"},
            "require_approval": {"type": "boolean", "description": "Require approval for timesheets"},
            "approval_period": {"type": "string", "description": "Approval period: weekly, biweekly, monthly"},
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        async with atomic(db):
            settings, created = await _q(TimesheetsSettings, db, hub_id).get_or_create()
            for field in ("default_billable", "require_approval", "approval_period"):
                if field in args:
                    setattr(settings, field, args[field])
            await db.flush()

        return {"updated": True}
