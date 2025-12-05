# Copyright (c) 2025, david-loe and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class EmployeeLeavePolicies(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        leave_policy: DF.Link
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        valid_from: DF.Date
    # end: auto-generated types
    pass

    # sadly validators on child tabels aren't called....
    def validate(self):
        from leave_dashboard.leave_dashboard.doctype.leave.leave import get_period

        self.valid_from, period_end = get_period(self.valid_from)
