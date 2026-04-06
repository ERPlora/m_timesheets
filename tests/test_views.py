"""
Tests for timesheets module views/routes.

Covers model properties, schema validation, route registration,
and helper functions. All async where applicable.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

import pytest

from timesheets.models import (
    APPROVAL_STATUS_LABELS,
    APPROVAL_STATUSES,
    ENTRY_STATUSES,
    STATUS_LABELS,
    TimeEntry,
    TimesheetApproval,
)
from timesheets.schemas import (
    ApprovalAction,
    HourlyRateCreate,
    HourlyRateUpdate,
    TimeEntryCreate,
    TimeEntryUpdate,
    TimesheetsSettingsUpdate,
)


# ============================================================================
# Model property tests
# ============================================================================


class TestTimeEntryProperties:
    """Tests for TimeEntry computed properties."""

    def test_status_label_draft(self, sample_time_entry):
        """Draft status should display as 'Draft'."""
        assert sample_time_entry.status_label == "Draft"

    def test_status_label_submitted(self, sample_time_entry_submitted):
        """Submitted status should display as 'Submitted'."""
        assert sample_time_entry_submitted.status_label == "Submitted"

    def test_status_label_approved(self, sample_time_entry_approved):
        """Approved status should display as 'Approved'."""
        assert sample_time_entry_approved.status_label == "Approved"

    def test_status_label_unknown(self, hub_id, employee_id):
        """Unknown status should fall back to the raw value."""
        entry = TimeEntry(
            hub_id=hub_id,
            employee_id=employee_id,
            date=datetime.date.today(),
            duration_minutes=60,
            status="custom_status",
        )
        assert entry.status_label == "custom_status"

    def test_duration_hours_conversion(self, sample_time_entry):
        """150 minutes should equal 2.5 hours."""
        assert sample_time_entry.duration_hours == 2.5

    def test_duration_hours_zero(self, hub_id, employee_id):
        """Zero duration should return 0.0 hours."""
        entry = TimeEntry(
            hub_id=hub_id,
            employee_id=employee_id,
            date=datetime.date.today(),
            duration_minutes=0,
        )
        assert entry.duration_hours == 0.0

    def test_duration_hours_exact_hour(self, hub_id, employee_id):
        """60 minutes should equal 1.0 hours."""
        entry = TimeEntry(
            hub_id=hub_id,
            employee_id=employee_id,
            date=datetime.date.today(),
            duration_minutes=60,
        )
        assert entry.duration_hours == 1.0

    def test_total_amount_calculation(self, sample_time_entry):
        """Total amount = rate * duration / 60, rounded to 2 decimal places."""
        # 25.00 * 150 / 60 = 62.50
        assert sample_time_entry.total_amount == Decimal("62.50")

    def test_total_amount_with_different_rate(self, hub_id, employee_id):
        """Total amount with 30.00/h for 120 min = 60.00."""
        entry = TimeEntry(
            hub_id=hub_id,
            employee_id=employee_id,
            date=datetime.date.today(),
            duration_minutes=120,
            rate_amount=Decimal("30.00"),
        )
        assert entry.total_amount == Decimal("60.00")

    def test_total_amount_none_when_no_rate(self, hub_id, employee_id):
        """Total amount should be None when rate_amount is not set."""
        entry = TimeEntry(
            hub_id=hub_id,
            employee_id=employee_id,
            date=datetime.date.today(),
            duration_minutes=120,
            rate_amount=None,
        )
        assert entry.total_amount is None

    def test_total_amount_none_when_no_duration(self, hub_id, employee_id):
        """Total amount should be None when duration_minutes is 0."""
        entry = TimeEntry(
            hub_id=hub_id,
            employee_id=employee_id,
            date=datetime.date.today(),
            duration_minutes=0,
            rate_amount=Decimal("25.00"),
        )
        assert entry.total_amount is None

    def test_repr(self, sample_time_entry):
        """Repr should include employee name, date, and duration."""
        r = repr(sample_time_entry)
        assert "Ana López" in r
        assert "2026-04-06" in r
        assert "150" in r


class TestTimesheetApprovalProperties:
    """Tests for TimesheetApproval computed properties."""

    def test_status_label_pending(self, sample_approval):
        """Pending status should display as 'Pending'."""
        assert sample_approval.status_label == "Pending"

    def test_status_label_approved(self, sample_approval_approved):
        """Approved status should display as 'Approved'."""
        assert sample_approval_approved.status_label == "Approved"

    def test_status_label_unknown(self, hub_id, employee_id):
        """Unknown status should fall back to the raw value."""
        approval = TimesheetApproval(
            hub_id=hub_id,
            employee_id=employee_id,
            period_start=datetime.date.today(),
            period_end=datetime.date.today(),
            status="unknown",
        )
        assert approval.status_label == "unknown"

    def test_repr(self, sample_approval):
        """Repr should include employee name and period dates."""
        r = repr(sample_approval)
        assert "Ana López" in r
        assert "2026-03-30" in r
        assert "2026-04-05" in r


class TestHourlyRateProperties:
    """Tests for HourlyRate model."""

    def test_repr(self, sample_hourly_rate):
        """Repr should include name and rate."""
        r = repr(sample_hourly_rate)
        assert "Standard" in r
        assert "25.00" in r

    def test_repr_inactive(self, sample_hourly_rate_inactive):
        """Repr for inactive rate should still include name and rate."""
        r = repr(sample_hourly_rate_inactive)
        assert "Deprecated" in r


class TestTimesheetsSettingsProperties:
    """Tests for TimesheetsSettings model."""

    def test_repr(self, sample_settings):
        """Repr should include hub_id reference."""
        r = repr(sample_settings)
        assert "TimesheetsSettings" in r


# ============================================================================
# Constants
# ============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_entry_statuses_tuple(self):
        """ENTRY_STATUSES should be a 4-element tuple."""
        assert len(ENTRY_STATUSES) == 4
        assert "draft" in ENTRY_STATUSES
        assert "submitted" in ENTRY_STATUSES
        assert "approved" in ENTRY_STATUSES
        assert "rejected" in ENTRY_STATUSES

    def test_status_labels_match_statuses(self):
        """Every entry status should have a label."""
        for status in ENTRY_STATUSES:
            assert status in STATUS_LABELS

    def test_approval_statuses_tuple(self):
        """APPROVAL_STATUSES should be a 3-element tuple."""
        assert len(APPROVAL_STATUSES) == 3
        assert "pending" in APPROVAL_STATUSES
        assert "approved" in APPROVAL_STATUSES
        assert "rejected" in APPROVAL_STATUSES

    def test_approval_status_labels_match(self):
        """Every approval status should have a label."""
        for status in APPROVAL_STATUSES:
            assert status in APPROVAL_STATUS_LABELS


# ============================================================================
# Schema validation tests
# ============================================================================


class TestTimeEntrySchemas:
    """Tests for TimeEntry Pydantic schemas."""

    def test_create_valid_minimal(self):
        """Create schema should accept date and duration only."""
        data = TimeEntryCreate(
            date=datetime.date(2026, 4, 6),
            duration_minutes=60,
        )
        assert data.date == datetime.date(2026, 4, 6)
        assert data.duration_minutes == 60
        assert data.billable is True
        assert data.description == ""

    def test_create_valid_full(self):
        """Create schema should accept all fields."""
        rate_id = uuid.uuid4()
        data = TimeEntryCreate(
            date=datetime.date(2026, 4, 6),
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0),
            duration_minutes=120,
            description="Feature work",
            billable=False,
            project_name="Project Alpha",
            client_name="BigCo",
            hourly_rate_id=rate_id,
        )
        assert data.start_time == datetime.time(9, 0)
        assert data.end_time == datetime.time(11, 0)
        assert data.billable is False
        assert data.project_name == "Project Alpha"
        assert data.hourly_rate_id == rate_id

    def test_create_duration_zero_rejected(self):
        """Duration must be at least 1 minute."""
        with pytest.raises(Exception):
            TimeEntryCreate(
                date=datetime.date(2026, 4, 6),
                duration_minutes=0,
            )

    def test_create_duration_negative_rejected(self):
        """Negative duration should be rejected."""
        with pytest.raises(Exception):
            TimeEntryCreate(
                date=datetime.date(2026, 4, 6),
                duration_minutes=-10,
            )

    def test_create_duration_exceeds_max_rejected(self):
        """Duration above 1440 (24h) should be rejected."""
        with pytest.raises(Exception):
            TimeEntryCreate(
                date=datetime.date(2026, 4, 6),
                duration_minutes=1441,
            )

    def test_create_duration_max_accepted(self):
        """Duration of 1440 (exactly 24h) should be accepted."""
        data = TimeEntryCreate(
            date=datetime.date(2026, 4, 6),
            duration_minutes=1440,
        )
        assert data.duration_minutes == 1440

    def test_update_partial(self):
        """Update schema should allow partial updates."""
        data = TimeEntryUpdate(description="Updated description")
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"description": "Updated description"}

    def test_update_empty(self):
        """Update schema should accept empty payload."""
        data = TimeEntryUpdate()
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {}

    def test_update_multiple_fields(self):
        """Update schema should accept multiple fields at once."""
        data = TimeEntryUpdate(
            duration_minutes=90,
            billable=False,
            project_name="New Project",
        )
        dumped = data.model_dump(exclude_unset=True)
        assert dumped["duration_minutes"] == 90
        assert dumped["billable"] is False
        assert dumped["project_name"] == "New Project"

    def test_update_duration_validation(self):
        """Update schema should reject invalid duration."""
        with pytest.raises(Exception):
            TimeEntryUpdate(duration_minutes=0)


class TestHourlyRateSchemas:
    """Tests for HourlyRate Pydantic schemas."""

    def test_create_valid(self):
        """Create schema should accept name and rate."""
        data = HourlyRateCreate(name="Senior Dev", rate=Decimal("75.00"))
        assert data.name == "Senior Dev"
        assert data.rate == Decimal("75.00")
        assert data.is_default is False
        assert data.is_active is True

    def test_create_with_employee(self):
        """Create schema should accept employee_id."""
        eid = uuid.uuid4()
        data = HourlyRateCreate(
            name="Personal Rate",
            rate=Decimal("40.00"),
            employee_id=eid,
            is_default=True,
        )
        assert data.employee_id == eid
        assert data.is_default is True

    def test_create_empty_name_rejected(self):
        """Name must have at least 1 character."""
        with pytest.raises(Exception):
            HourlyRateCreate(name="", rate=Decimal("25.00"))

    def test_create_negative_rate_rejected(self):
        """Rate must be >= 0."""
        with pytest.raises(Exception):
            HourlyRateCreate(name="Bad", rate=Decimal("-5.00"))

    def test_create_zero_rate_accepted(self):
        """Rate of 0 should be accepted (volunteer/internal)."""
        data = HourlyRateCreate(name="Volunteer", rate=Decimal("0.00"))
        assert data.rate == Decimal("0.00")

    def test_update_partial(self):
        """Update schema should allow partial updates."""
        data = HourlyRateUpdate(rate=Decimal("80.00"))
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"rate": Decimal("80.00")}

    def test_update_toggle_active(self):
        """Update schema should allow toggling is_active."""
        data = HourlyRateUpdate(is_active=False)
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"is_active": False}


class TestSettingsSchemas:
    """Tests for TimesheetsSettings Pydantic schemas."""

    def test_update_valid(self):
        """Settings update should accept valid values."""
        data = TimesheetsSettingsUpdate(
            default_billable=False,
            require_approval=False,
            approval_period="monthly",
        )
        assert data.default_billable is False
        assert data.approval_period == "monthly"

    def test_update_partial(self):
        """Settings update should allow partial payload."""
        data = TimesheetsSettingsUpdate(default_billable=True)
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"default_billable": True}

    def test_update_empty(self):
        """Settings update should accept empty payload."""
        data = TimesheetsSettingsUpdate()
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {}

    def test_approval_period_weekly(self):
        """Weekly approval period should be accepted."""
        data = TimesheetsSettingsUpdate(approval_period="weekly")
        assert data.approval_period == "weekly"

    def test_approval_period_biweekly(self):
        """Biweekly approval period should be accepted."""
        data = TimesheetsSettingsUpdate(approval_period="biweekly")
        assert data.approval_period == "biweekly"

    def test_approval_period_monthly(self):
        """Monthly approval period should be accepted."""
        data = TimesheetsSettingsUpdate(approval_period="monthly")
        assert data.approval_period == "monthly"

    def test_approval_period_invalid_rejected(self):
        """Invalid approval period should be rejected by regex pattern."""
        with pytest.raises(Exception):
            TimesheetsSettingsUpdate(approval_period="daily")

    def test_approval_period_empty_rejected(self):
        """Empty string approval period should be rejected by regex pattern."""
        with pytest.raises(Exception):
            TimesheetsSettingsUpdate(approval_period="")


class TestApprovalActionSchema:
    """Tests for ApprovalAction schema."""

    def test_with_notes(self):
        """ApprovalAction should accept notes."""
        data = ApprovalAction(notes="Needs corrections on Wednesday entries")
        assert data.notes == "Needs corrections on Wednesday entries"

    def test_empty_notes(self):
        """ApprovalAction should default to empty notes."""
        data = ApprovalAction()
        assert data.notes == ""


# ============================================================================
# Route registration tests
# ============================================================================


class TestRouterRegistration:
    """Verify timesheets router has the expected endpoints."""

    def test_router_exists(self):
        """Router should be importable."""
        from timesheets.routes import router
        assert router is not None

    def test_index_route(self):
        """GET / should be registered (my_time view)."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/" in paths

    def test_entry_add_route(self):
        """POST /entries/add should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/entries/add" in paths

    def test_entry_edit_route(self):
        """POST /entries/{entry_id}/edit should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/entries/{entry_id}/edit" in paths

    def test_entry_delete_route(self):
        """POST /entries/{entry_id}/delete should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/entries/{entry_id}/delete" in paths

    def test_entry_submit_route(self):
        """POST /entries/{entry_id}/submit should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/entries/{entry_id}/submit" in paths

    def test_approvals_route(self):
        """GET /approvals should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/approvals" in paths

    def test_approve_route(self):
        """POST /approvals/{entry_id}/approve should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/approvals/{entry_id}/approve" in paths

    def test_reject_route(self):
        """POST /approvals/{entry_id}/reject should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/approvals/{entry_id}/reject" in paths

    def test_reports_route(self):
        """GET /reports should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/reports" in paths

    def test_rates_route(self):
        """GET /rates should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/rates" in paths

    def test_rate_add_route(self):
        """POST /rates/add should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/rates/add" in paths

    def test_rate_edit_route(self):
        """POST /rates/{rate_id}/edit should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/rates/{rate_id}/edit" in paths

    def test_rate_delete_route(self):
        """POST /rates/{rate_id}/delete should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/rates/{rate_id}/delete" in paths

    def test_settings_route(self):
        """GET /settings should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/settings" in paths

    def test_settings_save_route(self):
        """POST /settings/save should be registered."""
        from timesheets.routes import router
        paths = [r.path for r in router.routes]
        assert "/settings/save" in paths


# ============================================================================
# Helper function tests
# ============================================================================


class TestWeekBounds:
    """Tests for the _week_bounds helper function."""

    def test_monday_returns_same_week(self):
        """A Monday should return itself as the start of the week."""
        from timesheets.routes import _week_bounds
        # 2026-04-06 is a Monday
        monday, sunday = _week_bounds(datetime.date(2026, 4, 6))
        assert monday == datetime.date(2026, 4, 6)
        assert sunday == datetime.date(2026, 4, 12)

    def test_wednesday_returns_correct_bounds(self):
        """A Wednesday should return the enclosing Monday-Sunday."""
        from timesheets.routes import _week_bounds
        # 2026-04-08 is a Wednesday
        monday, sunday = _week_bounds(datetime.date(2026, 4, 8))
        assert monday == datetime.date(2026, 4, 6)
        assert sunday == datetime.date(2026, 4, 12)

    def test_sunday_returns_same_week(self):
        """A Sunday should return the Monday of the same week."""
        from timesheets.routes import _week_bounds
        # 2026-04-12 is a Sunday
        monday, sunday = _week_bounds(datetime.date(2026, 4, 12))
        assert monday == datetime.date(2026, 4, 6)
        assert sunday == datetime.date(2026, 4, 12)

    def test_none_defaults_to_today(self):
        """Passing None should use today's date."""
        from timesheets.routes import _week_bounds
        monday, sunday = _week_bounds(None)
        today = datetime.date.today()
        assert monday <= today <= sunday
        assert monday.weekday() == 0  # Monday
        assert sunday.weekday() == 6  # Sunday
        assert (sunday - monday).days == 6

    def test_span_is_always_seven_days(self):
        """The week span should always be exactly 6 days (Mon-Sun)."""
        from timesheets.routes import _week_bounds
        for offset in range(7):
            ref = datetime.date(2026, 4, 6) + datetime.timedelta(days=offset)
            monday, sunday = _week_bounds(ref)
            assert (sunday - monday).days == 6


# ============================================================================
# Module manifest tests
# ============================================================================


class TestModuleManifest:
    """Tests for timesheets module.py manifest."""

    def test_module_id(self):
        """Module ID should be 'timesheets'."""
        from timesheets.module import MODULE_ID
        assert MODULE_ID == "timesheets"

    def test_module_version_format(self):
        """Module version should follow semver (X.Y.Z)."""
        from timesheets.module import MODULE_VERSION
        parts = MODULE_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_has_models(self):
        """Module should declare HAS_MODELS = True."""
        from timesheets.module import HAS_MODELS
        assert HAS_MODELS is True

    def test_dependencies(self):
        """Module should depend on staff."""
        from timesheets.module import DEPENDENCIES
        assert "staff" in DEPENDENCIES

    def test_navigation_tabs(self):
        """Module should declare 5 navigation tabs."""
        from timesheets.module import NAVIGATION
        assert len(NAVIGATION) == 5
        tab_ids = [tab["id"] for tab in NAVIGATION]
        assert "my_time" in tab_ids
        assert "approvals" in tab_ids
        assert "reports" in tab_ids
        assert "rates" in tab_ids
        assert "settings" in tab_ids

    def test_permissions_defined(self):
        """Module should define at least 7 permissions."""
        from timesheets.module import PERMISSIONS
        assert len(PERMISSIONS) >= 7
        perm_codes = [p[0] for p in PERMISSIONS]
        assert "view_time_entry" in perm_codes
        assert "approve_timesheet" in perm_codes
        assert "manage_rates" in perm_codes

    def test_role_permissions_admin_wildcard(self):
        """Admin role should have wildcard permissions."""
        from timesheets.module import ROLE_PERMISSIONS
        assert ROLE_PERMISSIONS["admin"] == ["*"]

    def test_role_permissions_employee_limited(self):
        """Employee role should only view/add/change entries."""
        from timesheets.module import ROLE_PERMISSIONS
        employee_perms = ROLE_PERMISSIONS["employee"]
        assert "approve_timesheet" not in employee_perms
        assert "manage_rates" not in employee_perms
        assert "view_time_entry" in employee_perms

    def test_menu_defined(self):
        """Module should define a sidebar menu entry."""
        from timesheets.module import MENU
        assert MENU["label"] == "Timesheets"
        assert "icon" in MENU
        assert "order" in MENU
