"""
Timesheets module hook registrations.

Registers actions and filters on the HookRegistry during module load.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.hooks.registry import HookRegistry

MODULE_ID = "timesheets"


def register_hooks(hooks: HookRegistry, module_id: str) -> None:
    """
    Register hooks for the timesheets module.

    Called by ModuleRuntime during module load.
    """
    # Action: after time entry approved — other modules can subscribe
    hooks.add_action(
        "timesheets.entry_approved",
        _on_entry_approved,
        priority=10,
        module_id=module_id,
    )

    # Action: after timesheet period approved
    hooks.add_action(
        "timesheets.period_approved",
        _on_period_approved,
        priority=10,
        module_id=module_id,
    )


async def _on_entry_approved(
    entry=None,
    session=None,
    **kwargs,
) -> None:
    """
    Default action when a time entry is approved.
    Other modules (invoicing, payroll) can subscribe to extend.
    """


async def _on_period_approved(
    approval=None,
    session=None,
    **kwargs,
) -> None:
    """
    Default action when a timesheet period is approved.
    Other modules can subscribe to generate invoices, payroll, etc.
    """
