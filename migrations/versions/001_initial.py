"""Initial timesheets module schema.

Revision ID: 001
Revises: -
Create Date: 2026-04-05

Creates tables: timesheets_settings, timesheets_hourly_rate,
timesheets_time_entry, timesheets_approval.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # TimesheetsSettings
    op.create_table(
        "timesheets_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hub_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("default_billable", sa.Boolean(), server_default="true"),
        sa.Column("require_approval", sa.Boolean(), server_default="true"),
        sa.Column("approval_period", sa.String(20), server_default="weekly"),
        sa.UniqueConstraint("hub_id", name="uq_timesheets_settings_hub"),
    )

    # HourlyRate
    op.create_table(
        "timesheets_hourly_rate",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hub_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )
    op.create_index("ix_timesheets_rate_hub_name", "timesheets_hourly_rate", ["hub_id", "name"])

    # TimeEntry
    op.create_table(
        "timesheets_time_entry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hub_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("employee_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("employee_name", sa.String(255), server_default=""),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("billable", sa.Boolean(), server_default="true"),
        sa.Column("project_name", sa.String(200), server_default=""),
        sa.Column("client_name", sa.String(200), server_default=""),
        sa.Column("hourly_rate_id", sa.Uuid(), sa.ForeignKey("timesheets_hourly_rate.id"), nullable=True),
        sa.Column("rate_amount", sa.Numeric(10, 2), nullable=True),
    )
    op.create_index("ix_timesheets_entry_hub_employee", "timesheets_time_entry", ["hub_id", "employee_id"])
    op.create_index("ix_timesheets_entry_hub_date", "timesheets_time_entry", ["hub_id", "date"])
    op.create_index("ix_timesheets_entry_hub_status", "timesheets_time_entry", ["hub_id", "status"])

    # TimesheetApproval
    op.create_table(
        "timesheets_approval",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hub_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("employee_name", sa.String(255), server_default=""),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_hours", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("billable_hours", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("notes", sa.Text(), server_default=""),
    )
    op.create_index("ix_timesheets_approval_hub_employee", "timesheets_approval", ["hub_id", "employee_id"])
    op.create_index("ix_timesheets_approval_hub_status", "timesheets_approval", ["hub_id", "status"])
    op.create_index("ix_timesheets_approval_hub_period", "timesheets_approval", ["hub_id", "period_start"])


def downgrade() -> None:
    op.drop_table("timesheets_approval")
    op.drop_table("timesheets_time_entry")
    op.drop_table("timesheets_hourly_rate")
    op.drop_table("timesheets_settings")
