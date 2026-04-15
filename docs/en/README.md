# Timesheets (module: `timesheets`)

Employee time tracking, billable hours, approvals, and hourly rates.

## Purpose

The Timesheets module tracks project-oriented or billable time entries submitted by employees. Unlike `time_control` (which records raw clock-in/out events for compliance), timesheets are manually entered work entries that go through an approval workflow before being used for billing or payroll.

Employees submit time entries (date, hours, description, billable flag, hourly rate), which managers review and approve or reject. Approved entries feed into payroll calculations via the `timesheets.entry_approved` hook. The module supports configurable hourly rates (global default, per-employee override) and generates period-based reports.

Migrated from hub legacy (Django) to hub-next (FastAPI + SQLAlchemy 2.0).

## Models

- `TimesheetsSettings` — Singleton per hub. Default billable flag, require_approval flag, approval period (weekly/biweekly/monthly).
- `HourlyRate` — Named rate definition with amount, optional employee scope, is_default flag, is_active.
- `TimeEntry` — Individual time record: employee reference, date, start/end time, duration, description, is_billable, hourly rate reference, status (draft/submitted/approved/rejected), notes.
- `TimesheetApproval` — Approval record for a time period: employee, period start/end, status, approver reference, approval date, notes.

## Routes

`GET /m/timesheets/my_time` — Employee's own time entries
`GET /m/timesheets/approvals` — Manager approval queue
`GET /m/timesheets/reports` — Hours and billing reports
`GET /m/timesheets/rates` — Hourly rate management
`GET /m/timesheets/settings` — Module settings

## Events

### Consumed

`staff.member_deactivated` — Logged for audit; pending entries remain but are flagged.

## Hooks

### Emitted

`timesheets.entry_approved` — Fired after an individual time entry is approved. Payload: `entry`.
`timesheets.period_approved` — Fired after a full timesheet period is approved. Payload: `approval`.

## Dependencies

- `staff`

## Pricing

Free.
