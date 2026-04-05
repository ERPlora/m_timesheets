"""
Timesheets module AI context — injected into the LLM system prompt.

Provides the LLM with knowledge about the module's models, relationships,
and standard operating procedures.
"""

CONTEXT = """
## Timesheets Module

Employee time tracking, billable hours, approvals, and hourly rate management.

### TimesheetsSettings (singleton per hub)
- default_billable (bool, default True): new time entries default to billable
- require_approval (bool, default True): entries must be approved before billing
- approval_period (choice): weekly, biweekly, monthly

### HourlyRate Model
- name (str): rate label (e.g. "Standard", "Senior Developer", "Overtime")
- rate (Decimal): amount per hour
- employee_id (UUID, nullable): if set, rate is specific to this employee; null = global rate
- is_default (bool): used when no rate is specified on a time entry
- is_active (bool): inactive rates are hidden from selection

### TimeEntry Model
- employee_id (UUID): who logged the time
- employee_name (str): snapshot of employee name
- date (Date): work date
- start_time / end_time (Time, nullable): optional clock-in/clock-out
- duration_minutes (int): total duration (manual or computed from start/end)
- description (Text): what was worked on
- status (choice): draft, submitted, approved, rejected
- billable (bool): whether this time is billable
- project_name (str, nullable): project or task reference
- client_name (str, nullable): client reference
- hourly_rate_id (FK to HourlyRate, nullable)
- rate_amount (Decimal, nullable): snapshot of rate at time of entry
- Computed properties: duration_hours = minutes / 60, total_amount = rate_amount * hours

### TimesheetApproval Model
- employee_id (UUID), employee_name (str)
- period_start / period_end (Date): the period covered
- status (choice): pending, approved, rejected
- approved_by (UUID, nullable): manager who approved/rejected
- approved_at (DateTime, nullable)
- total_hours / billable_hours (Decimal): aggregated from entries
- notes (Text)

### Key Flows
1. **Log time**: create TimeEntry with employee, date, duration_minutes, description. Status = draft.
2. **Submit**: update TimeEntry status to "submitted".
3. **Approve**: manager sets status = "approved".
4. **Reject**: manager sets status = "rejected" with notes.
5. **Billable amount**: sum TimeEntry.total_amount where billable=True and status=approved.

### Dependencies
- Requires: staff module (employee profiles)
"""

SOPS = [
    {
        "id": "log_time",
        "triggers_es": ["registrar tiempo", "registrar horas", "fichar horas"],
        "triggers_en": ["log time", "track time", "add time entry"],
        "steps": ["create_time_entry"],
        "modules_required": ["timesheets"],
    },
    {
        "id": "check_hours_this_week",
        "triggers_es": ["horas esta semana", "tiempo registrado", "cuantas horas"],
        "triggers_en": ["hours this week", "time logged", "how many hours"],
        "steps": ["list_time_entries"],
        "modules_required": ["timesheets"],
    },
    {
        "id": "approve_timesheets",
        "triggers_es": ["aprobar hojas de tiempo", "aprobar timesheets"],
        "triggers_en": ["approve timesheets", "review time entries"],
        "steps": ["list_time_entries", "update_time_entry"],
        "modules_required": ["timesheets"],
    },
    {
        "id": "manage_rates",
        "triggers_es": ["tarifas por hora", "gestionar tarifas"],
        "triggers_en": ["hourly rates", "manage rates"],
        "steps": ["list_hourly_rates"],
        "modules_required": ["timesheets"],
    },
]
