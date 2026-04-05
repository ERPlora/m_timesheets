"""
Timesheets module slot registrations.

Defines slots that OTHER modules can fill (e.g. time entry extras, report widgets).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.slots import SlotRegistry

MODULE_ID = "timesheets"


def register_slots(slots: SlotRegistry, module_id: str) -> None:
    """
    Register slot definitions owned by the timesheets module.

    Other modules can register content INTO these slots.
    The timesheets module declares the extension points.

    Called by ModuleRuntime during module load.
    """
    # Future extension points:
    # - timesheets.entry_form_extras: additional fields in time entry form
    # - timesheets.report_widgets: extra report sections
