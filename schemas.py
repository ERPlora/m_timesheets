"""
Pydantic schemas for timesheets module.

Replaces Django forms — used for request validation and form rendering.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


# ============================================================================
# Settings
# ============================================================================

class TimesheetsSettingsUpdate(BaseModel):
    default_billable: bool | None = None
    require_approval: bool | None = None
    approval_period: str | None = Field(default=None, pattern="^(weekly|biweekly|monthly)$")


# ============================================================================
# Hourly Rate
# ============================================================================

class HourlyRateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rate: Decimal = Field(ge=Decimal("0"), decimal_places=2)
    employee_id: uuid.UUID | None = None
    is_default: bool = False
    is_active: bool = True


class HourlyRateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    rate: Decimal | None = Field(default=None, ge=Decimal("0"))
    employee_id: uuid.UUID | None = None
    is_default: bool | None = None
    is_active: bool | None = None


# ============================================================================
# Time Entry
# ============================================================================

class TimeEntryCreate(BaseModel):
    date: datetime.date
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None
    duration_minutes: int = Field(ge=1, le=1440)
    description: str = ""
    billable: bool = True
    project_name: str = ""
    client_name: str = ""
    hourly_rate_id: uuid.UUID | None = None


class TimeEntryUpdate(BaseModel):
    date: datetime.date | None = None
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    description: str | None = None
    billable: bool | None = None
    project_name: str | None = None
    client_name: str | None = None
    hourly_rate_id: uuid.UUID | None = None


# ============================================================================
# Approval
# ============================================================================

class ApprovalAction(BaseModel):
    notes: str = ""
