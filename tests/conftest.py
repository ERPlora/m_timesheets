"""
Test fixtures for the timesheets module.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal

import pytest

from timesheets.models import (
    HourlyRate,
    TimeEntry,
    TimesheetApproval,
    TimesheetsSettings,
)


@pytest.fixture
def hub_id():
    """Test hub UUID."""
    return uuid.uuid4()


@pytest.fixture
def employee_id():
    """Test employee UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_settings(hub_id):
    """Create a sample timesheets settings instance (not persisted)."""
    return TimesheetsSettings(
        hub_id=hub_id,
        default_billable=True,
        require_approval=True,
        approval_period="weekly",
    )


@pytest.fixture
def sample_hourly_rate(hub_id):
    """Create a sample hourly rate instance (not persisted)."""
    return HourlyRate(
        hub_id=hub_id,
        name="Standard",
        rate=Decimal("25.00"),
        is_default=True,
        is_active=True,
    )


@pytest.fixture
def sample_hourly_rate_inactive(hub_id):
    """Create an inactive hourly rate instance (not persisted)."""
    return HourlyRate(
        hub_id=hub_id,
        name="Deprecated",
        rate=Decimal("15.00"),
        is_default=False,
        is_active=False,
    )


@pytest.fixture
def sample_time_entry(hub_id, employee_id):
    """Create a sample time entry instance (not persisted)."""
    return TimeEntry(
        hub_id=hub_id,
        employee_id=employee_id,
        employee_name="Ana López",
        date=date(2026, 4, 6),
        start_time=time(9, 0),
        end_time=time(11, 30),
        duration_minutes=150,
        description="Backend development",
        status="draft",
        billable=True,
        project_name="ERPlora v3",
        client_name="ACME Corp",
        rate_amount=Decimal("25.00"),
    )


@pytest.fixture
def sample_time_entry_submitted(hub_id, employee_id):
    """Create a submitted time entry instance (not persisted)."""
    return TimeEntry(
        hub_id=hub_id,
        employee_id=employee_id,
        employee_name="Ana López",
        date=date(2026, 4, 5),
        start_time=time(14, 0),
        end_time=time(16, 0),
        duration_minutes=120,
        description="Code review",
        status="submitted",
        billable=True,
        project_name="ERPlora v3",
        client_name="ACME Corp",
        rate_amount=Decimal("30.00"),
    )


@pytest.fixture
def sample_time_entry_approved(hub_id, employee_id):
    """Create an approved time entry instance (not persisted)."""
    return TimeEntry(
        hub_id=hub_id,
        employee_id=employee_id,
        employee_name="Ana López",
        date=date(2026, 4, 4),
        duration_minutes=480,
        description="Sprint planning",
        status="approved",
        billable=False,
    )


@pytest.fixture
def sample_approval(hub_id, employee_id):
    """Create a sample timesheet approval instance (not persisted)."""
    return TimesheetApproval(
        hub_id=hub_id,
        employee_id=employee_id,
        employee_name="Ana López",
        period_start=date(2026, 3, 30),
        period_end=date(2026, 4, 5),
        status="pending",
        total_hours=Decimal("40.00"),
        billable_hours=Decimal("32.50"),
        notes="",
    )


@pytest.fixture
def sample_approval_approved(hub_id, employee_id):
    """Create an approved timesheet approval instance (not persisted)."""
    return TimesheetApproval(
        hub_id=hub_id,
        employee_id=employee_id,
        employee_name="Ana López",
        period_start=date(2026, 3, 23),
        period_end=date(2026, 3, 29),
        status="approved",
        approved_by=uuid.uuid4(),
        total_hours=Decimal("38.00"),
        billable_hours=Decimal("30.00"),
        notes="All good",
    )
