"""
Timesheets module AI tools for the assistant.

Tools for querying time entries, managing rates, approvals, and settings.
"""

from __future__ import annotations


# AI tools will be registered here following the same @register_tool pattern.
# The timesheets module exposes tools for:
# - list_time_entries: Query entries by employee, date, status, project
# - get_time_entry: Get full details of a specific entry
# - create_time_entry: Log a new time entry
# - update_time_entry: Update entry fields
# - delete_time_entry: Delete a time entry
# - list_hourly_rates: List configured rates
# - create_hourly_rate: Add a new rate
# - update_hourly_rate: Update a rate
# - delete_hourly_rate: Delete a rate
# - list_timesheet_approvals: List approval records
# - get_timesheet_approval: Get approval details
# - update_timesheet_approval: Approve or reject
# - get_timesheets_settings: Read current settings
# - update_timesheets_settings: Update settings

TOOLS = []
