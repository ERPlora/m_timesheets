"""
Timesheets module services — ModuleService pattern for AI assistant integration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal

from runtime.orm.transactions import atomic
from runtime.apps.service_facade import ModuleService, action

from .models import HourlyRate, TimeEntry, TimesheetsSettings


class TimesheetService(ModuleService):
    """Time entries, hourly rates, and timesheet settings."""

    @action(permission="view_time_entry")
    async def list_entries(
        self,
        *,
        employee_id: str = "",
        status: str = "",
        date_from: str = "",
        date_to: str = "",
        project_name: str = "",
        billable: bool | None = None,
        limit: int = 20,
    ) -> dict:
        """List time entries with optional filters."""
        query = self.q(TimeEntry)

        if employee_id:
            query = query.filter(TimeEntry.employee_id == uuid.UUID(employee_id))
        if status:
            query = query.filter(TimeEntry.status == status)
        if date_from:
            d = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(TimeEntry.date >= d)
        if date_to:
            d = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(TimeEntry.date <= d)
        if project_name:
            query = query.filter(TimeEntry.project_name.ilike(f"%{project_name}%"))
        if billable is not None:
            query = query.filter(TimeEntry.billable == billable)

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

    @action(permission="add_time_entry", mutates=True)
    async def create_entry(
        self,
        *,
        employee_id: str,
        employee_name: str,
        date: str,
        duration_minutes: int,
        description: str = "",
        project_name: str = "",
        client_name: str = "",
        billable: bool = True,
        hourly_rate_id: str = "",
    ) -> dict:
        """Create a new time entry."""
        entry_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.now(UTC).date()

        if entry_date > today:
            return {"error": "Cannot create time entries in the future"}

        if duration_minutes <= 0:
            return {"error": "Duration must be positive"}

        rate_amount = None
        rate_id = None
        if hourly_rate_id:
            rate_id = uuid.UUID(hourly_rate_id)
            hr = await self.q(HourlyRate).get(rate_id)
            if hr:
                rate_amount = hr.rate

        async with atomic(self.db) as session:
            e = TimeEntry(
                hub_id=self.hub_id,
                employee_id=uuid.UUID(employee_id),
                employee_name=employee_name,
                date=entry_date,
                duration_minutes=duration_minutes,
                description=description,
                project_name=project_name,
                client_name=client_name,
                billable=billable,
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

    @action(permission="change_time_entry", mutates=True)
    async def update_entry(
        self,
        *,
        entry_id: str,
        duration_minutes: int | None = None,
        description: str | None = None,
        project_name: str | None = None,
        client_name: str | None = None,
        billable: bool | None = None,
    ) -> dict:
        """Update an existing time entry. Cannot modify approved entries."""
        e = await self.q(TimeEntry).get(uuid.UUID(entry_id))
        if e is None:
            return {"error": "Time entry not found"}

        if e.status == "approved":
            return {"error": "Cannot modify an approved time entry"}

        if duration_minutes is not None and duration_minutes <= 0:
            return {"error": "Duration must be positive"}

        async with atomic(self.db):
            if description is not None:
                e.description = description
            if project_name is not None:
                e.project_name = project_name
            if client_name is not None:
                e.client_name = client_name
            if duration_minutes is not None:
                e.duration_minutes = duration_minutes
            if billable is not None:
                e.billable = billable
            await self.db.flush()

        return {"id": str(e.id), "updated": True}

    @action(permission="delete_time_entry", mutates=True)
    async def delete_entry(self, *, entry_id: str) -> dict:
        """Delete a time entry. Cannot delete approved entries."""
        e = await self.q(TimeEntry).get(uuid.UUID(entry_id))
        if e is None:
            return {"error": "Time entry not found"}

        if e.status == "approved":
            return {"error": "Cannot delete an approved time entry"}

        async with atomic(self.db):
            e.is_deleted = True
            e.deleted_at = datetime.now(UTC)
            await self.db.flush()

        return {"id": str(e.id), "deleted": True}

    @action(permission="view_time_entry")
    async def list_hourly_rates(self) -> dict:
        """List all active hourly rates."""
        rates = await self.q(HourlyRate).filter(
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

    @action(permission="manage_rates", mutates=True)
    async def create_hourly_rate(
        self,
        *,
        name: str,
        rate: str,
        employee_id: str = "",
        is_default: bool = False,
    ) -> dict:
        """Create a new hourly rate."""
        rate_val = Decimal(rate)
        if rate_val <= 0:
            return {"error": "Rate must be positive"}

        async with atomic(self.db) as session:
            r = HourlyRate(
                hub_id=self.hub_id,
                name=name,
                rate=rate_val,
                employee_id=uuid.UUID(employee_id) if employee_id else None,
                is_default=is_default,
            )
            session.add(r)
            await session.flush()

        return {"id": str(r.id), "name": r.name, "rate": str(r.rate), "created": True}

    @action(permission="view_settings")
    async def get_settings(self) -> dict:
        """Get current timesheets settings."""
        settings = await self.q(TimesheetsSettings).first()
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

    @action(permission="change_settings", mutates=True)
    async def update_settings(
        self,
        *,
        default_billable: bool | None = None,
        require_approval: bool | None = None,
        approval_period: str | None = None,
    ) -> dict:
        """Update timesheets settings."""
        async with atomic(self.db):
            settings, created = await self.q(TimesheetsSettings).get_or_create()
            fields = {
                "default_billable": default_billable,
                "require_approval": require_approval,
                "approval_period": approval_period,
            }
            for field, value in fields.items():
                if value is not None:
                    setattr(settings, field, value)
            await self.db.flush()

        return {"updated": True}
