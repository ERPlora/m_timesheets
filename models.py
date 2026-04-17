"""
Timesheets module models — SQLAlchemy 2.0.

Models: TimesheetsSettings, HourlyRate, TimeEntry, TimesheetApproval.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from runtime.models.base import HubBaseModel


# ============================================================================
# Timesheets Settings (singleton per hub)
# ============================================================================

class TimesheetsSettings(HubBaseModel):
    """Per-hub timesheets configuration."""

    __tablename__ = "timesheets_settings"
    __table_args__ = (
        UniqueConstraint("hub_id", name="uq_timesheets_settings_hub"),
    )

    default_billable: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )
    require_approval: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )
    approval_period: Mapped[str] = mapped_column(
        String(20), default="weekly", server_default="weekly",
    )

    def __repr__(self) -> str:
        return f"<TimesheetsSettings hub={self.hub_id}>"


# ============================================================================
# Hourly Rate
# ============================================================================

class HourlyRate(HubBaseModel):
    """Hourly billing rate configuration."""

    __tablename__ = "timesheets_hourly_rate"
    __table_args__ = (
        Index("ix_timesheets_rate_hub_name", "hub_id", "name"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )

    # Relationships
    time_entries: Mapped[list[TimeEntry]] = relationship(
        "TimeEntry", back_populates="hourly_rate_rel", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<HourlyRate {self.name!r} ({self.rate}/h)>"


# ============================================================================
# Time Entry
# ============================================================================

ENTRY_STATUSES = ("draft", "submitted", "approved", "rejected")

STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Submitted",
    "approved": "Approved",
    "rejected": "Rejected",
}


class TimeEntry(HubBaseModel):
    """Individual time log entry for an employee."""

    __tablename__ = "timesheets_time_entry"
    __table_args__ = (
        Index("ix_timesheets_entry_hub_employee", "hub_id", "employee_id"),
        Index("ix_timesheets_entry_hub_date", "hub_id", "date"),
        Index("ix_timesheets_entry_hub_status", "hub_id", "status"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True,
    )
    employee_name: Mapped[str] = mapped_column(
        String(255), default="", server_default="",
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(
        Text, default="", server_default="",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft",
    )
    billable: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )
    project_name: Mapped[str] = mapped_column(
        String(200), default="", server_default="",
    )
    client_name: Mapped[str] = mapped_column(
        String(200), default="", server_default="",
    )
    hourly_rate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("timesheets_hourly_rate.id"), nullable=True,
    )
    rate_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True,
    )

    # Relationships
    hourly_rate_rel: Mapped[HourlyRate | None] = relationship(
        "HourlyRate", back_populates="time_entries", lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<TimeEntry {self.employee_name} {self.date} ({self.duration_minutes}m)>"

    async def get_employee(self, session: object) -> object | None:
        """Return StaffMember for this entry, or None if not found / staff module unavailable."""
        try:
            from staff.models import StaffMember  # lazy cross-module import
        except ImportError:
            return None
        from sqlalchemy import select
        stmt = select(StaffMember).where(
            StaffMember.hub_id == self.hub_id,
            StaffMember.id == self.employee_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def duration_hours(self) -> float:
        return round(self.duration_minutes / 60, 2) if self.duration_minutes else 0.0

    @property
    def total_amount(self) -> Decimal | None:
        if self.rate_amount and self.duration_minutes:
            return (self.rate_amount * Decimal(str(self.duration_minutes)) / Decimal("60")).quantize(Decimal("0.01"))
        return None


# ============================================================================
# Timesheet Approval
# ============================================================================

APPROVAL_STATUSES = ("pending", "approved", "rejected")

APPROVAL_STATUS_LABELS = {
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
}


class TimesheetApproval(HubBaseModel):
    """Approval batch for an employee's time period."""

    __tablename__ = "timesheets_approval"
    __table_args__ = (
        Index("ix_timesheets_approval_hub_employee", "hub_id", "employee_id"),
        Index("ix_timesheets_approval_hub_status", "hub_id", "status"),
        Index("ix_timesheets_approval_hub_period", "hub_id", "period_start"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    employee_name: Mapped[str] = mapped_column(
        String(255), default="", server_default="",
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending",
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    total_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    billable_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    notes: Mapped[str] = mapped_column(
        Text, default="", server_default="",
    )

    def __repr__(self) -> str:
        return f"<TimesheetApproval {self.employee_name} ({self.period_start} - {self.period_end})>"

    @property
    def status_label(self) -> str:
        return APPROVAL_STATUS_LABELS.get(self.status, self.status)
