"""
Timesheets module manifest.

Employee time tracking, billable hours, approvals, and hourly rate management.
Migrated from hub legacy (Django) to hub-next (FastAPI + SQLAlchemy 2.0).
"""


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------
MODULE_ID = "timesheets"
MODULE_NAME = "Timesheets"
MODULE_VERSION = "2.0.4"
MODULE_ICON = "document-text-outline"
MODULE_DESCRIPTION = "Employee time tracking, billable hours, approvals, and hourly rates"
MODULE_AUTHOR = "ERPlora"
MODULE_CATEGORY = "hr"

# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------
HAS_MODELS = True
MIDDLEWARE = ""

# ---------------------------------------------------------------------------
# Menu (sidebar entry)
# ---------------------------------------------------------------------------
MENU = {
    "label": "Timesheets",
    "icon": "document-text-outline",
    "order": 44,
}

# ---------------------------------------------------------------------------
# Navigation tabs (bottom tabbar in module views)
# ---------------------------------------------------------------------------
NAVIGATION = [
    {"id": "my_time", "label": "My Time", "icon": "time-outline", "view": "my_time"},
    {"id": "approvals", "label": "Approvals", "icon": "checkmark-circle-outline", "view": "approvals"},
    {"id": "reports", "label": "Reports", "icon": "bar-chart-outline", "view": "reports"},
    {"id": "rates", "label": "Rates", "icon": "cash-outline", "view": "rates"},
    {"id": "settings", "label": "Settings", "icon": "settings-outline", "view": "settings"},
]

# ---------------------------------------------------------------------------
# Dependencies (other modules required to be active)
# ---------------------------------------------------------------------------
DEPENDENCIES: list[str] = ["staff"]

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
PERMISSIONS = [
    ("view_time_entry", "View time entries"),
    ("add_time_entry", "Add time entries"),
    ("change_time_entry", "Edit time entries"),
    ("delete_time_entry", "Delete time entries"),
    ("approve_timesheet", "Approve timesheets"),
    ("manage_rates", "Manage hourly rates"),
    ("view_reports", "View reports"),
    ("view_settings", "View settings"),
    ("change_settings", "Change settings"),
]

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "manager": [
        "view_time_entry", "add_time_entry", "change_time_entry",
        "approve_timesheet", "manage_rates", "view_reports", "view_settings",
    ],
    "employee": ["view_time_entry", "add_time_entry", "change_time_entry"],
}

# ---------------------------------------------------------------------------
# Scheduled tasks
# ---------------------------------------------------------------------------
SCHEDULED_TASKS: list[dict] = []

# ---------------------------------------------------------------------------
# Pricing (free module)
# ---------------------------------------------------------------------------
# PRICING = {"monthly": 0, "yearly": 0}
