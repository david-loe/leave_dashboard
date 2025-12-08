# Copyright (c) 2025, david-loe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

import frappe
from frappe.model.document import Document
from leave_dashboard.leave_dashboard.doctype.leave.leave import get_period
from hrms.hr.doctype.leave_application.leave_application import get_leave_details
from frappe.utils import now_datetime, getdate, DateTimeLikeObject


class LeaveSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        period_length: DF.Literal["12", "6", "4", "3", "2", "1"]
        period_start: DF.Date
    # end: auto-generated types
    pass


@frappe.whitelist()
def migrate_from_hrms_leave_applications(date_input: DateTimeLikeObject | None = None):
    if not date_input:
        date = now_datetime().date()
    else:
        date = getdate(date_input)
    leave_types = frappe.db.get_all("Leave Type", filters={"allow_negative": 0}, fields=["name"])
    period_start, period_end = get_period(date)
    Emp = frappe.qb.DocType("Employee")
    employees = (
        frappe.qb.select(Emp.name)
        .from_(Emp)
        .where(Emp.status == "Active")
        .where(Emp.branch.notnull())
        .run(as_dict=True)
    )

    allocations = {}
    for employee in employees:
        leave_details = get_leave_details(employee["name"], date)
        for leave_type in leave_types:
            if leave_type["name"] in leave_details["leave_allocation"]:
                allocation: float = leave_details["leave_allocation"][leave_type["name"]]["total_leaves"]
                if allocation:
                    if leave_type["name"] not in allocations:
                        allocations[leave_type["name"]] = {}
                    if allocation not in allocations[leave_type["name"]]:
                        allocations[leave_type["name"]][allocation] = []
                    allocations[leave_type["name"]][allocation].append(employee["name"])

    for leave_type_name in allocations:
        for allocation in allocations[leave_type_name]:
            policy = frappe.new_doc(
                doctype="Leave Policy",
                title=f"Migration {leave_type_name}",
                leave_policy_details=[
                    {"leave_type": leave_type_name, "annual_allocation": allocation},
                ],
            )
            policy.insert(set_name=f"M-{leave_type_name}-{allocation:.1f}")
            for employee_name in allocations[leave_type_name][allocation]:
                emp_policy = frappe.new_doc(
                    doctype="Employee Leave Policies",
                    parent=employee_name,
                    parenttype="Employee",
                    parentfield="leave_policies",
                    valid_from=period_start,
                    leave_policy=policy.name,
                )
                emp_policy.insert()

    Application = frappe.qb.DocType("Leave Application")
    employee_names = [e["name"] for e in employees]
    applications = (
        frappe.qb.select(Application.star)
        .from_(Application)
        .where(Application.status.isin(["Open", "Approved"]))
        .where(Application.employee.isin(employee_names))
        .where(Application.docstatus < 2)
        .where(Application.from_date <= period_end)
        .where(Application.to_date >= period_start)
        .run(as_dict=True)
    )

    for application in applications:
        leave_dict = map_applications_to_leave(application)
        docstatus = leave_dict.pop("docstatus", None)
        status = leave_dict.pop("status", None)
        leave = frappe.new_doc(doctype="Leave", **leave_dict)
        leave.insert()

        if status == "Approved":
            from frappe.model.workflow import apply_workflow

            apply_workflow(leave, "Approve")

    return allocations


half_day_cache = {}


def map_applications_to_leave(application: dict):
    leave = {
        "amended_from": application.get("amended_from"),
        "employee": application.get("employee"),
        "from_date": application.get("from_date"),
        "from_time": "Morning",
        "leave_approver": application.get("leave_approver"),
        "leave_type": application.get("leave_type"),
        "posting_date": application.get("posting_date"),
        "reason": application.get("reason"),
        "status": application.get("status"),
        "docstatus": application.get("docstatus"),
        "to_date": application.get("to_date"),
        "to_time": "Evening",
        "total_leave_days": None,
    }
    if application["half_day"] == 1:
        if application["from_date"] == application["to_date"]:
            cache_value = 0
            if (
                application["employee"] in half_day_cache
                and application["from_date"] in half_day_cache[application["employee"]]
            ):
                cache_value = half_day_cache[application["employee"]][application["from_date"]]
            if cache_value == 0:
                leave["from_time"] = "Noon"
            elif cache_value == 1:
                leave["to_time"] = "Noon"
            else:
                raise (Exception("To Many half_day leaves on one day"))
            if not application["employee"] in half_day_cache:
                half_day_cache[application["employee"]] = {}
            half_day_cache[application["employee"]][application["from_date"]] = cache_value + 1

        elif application["half_day_date"]:
            if application["half_day_date"] == application["from_date"]:
                leave["from_time"] = "Noon"
            if application["half_day_date"] == application["to_date"]:
                leave["to_time"] = "Noon"
            else:
                leave["from_time"] = "Noon"
    return leave
