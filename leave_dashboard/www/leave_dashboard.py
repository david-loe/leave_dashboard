# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from datetime import datetime, timedelta, date
import frappe
from frappe import _
import json
import re
import unicodedata

from frappe.utils import now_datetime


no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)

    context.current_user = frappe.get_doc("User", frappe.session.user)

    roles = frappe.get_roles()
    if "Employee" not in roles:
        frappe.throw("Not permitted", frappe.PermissionError)

    settings = frappe.get_single("Leave Dashboard Settings")

    today = now_datetime().date()
    from_date = today - timedelta(days=settings.data_days_in_past)
    to_date = today + timedelta(days=settings.data_days_in_future)

    context.settings_json = json.dumps(settings.as_dict(), cls=DateTimeEncoder)
    leave_data = get_leave_data(from_date, to_date)
    branches = set(emp["branch"] for emp in leave_data)
    context.leave_data_json = json.dumps(leave_data, cls=DateTimeEncoder)
    context.holiday_lists_json = json.dumps(get_holiday_lists(branches, from_date, to_date), cls=DateTimeEncoder)
    leave_types = get_leave_types()
    context.leave_types_json = json.dumps(leave_types)
    leave_types.append({"className": "default-leave", "color": settings.default_leave_color})
    context.leave_types_css = build_background_border_css(leave_types)


def get_leave_data(from_date: datetime, to_date: datetime):
    from leave_dashboard.leave_dashboard.doctype.leave.leave import get_holiday_weekdays

    employees = frappe.db.get_all(
        "Employee",
        filters={"status": "Active", "branch": ["is", "set"]},
        fields=["name", "first_name", "last_name", "branch", "employee_name", "user_id"],
        order_by="last_name asc",
    )
    leaves = frappe.db.get_all(
        "Leave",
        filters={
            "status": ["in", ["Open", "Approved"]],
            "docstatus": ["<", 2],
            "to_date": [">=", from_date],
            "from_date": ["<=", to_date],
        },
        fields=["from_date", "from_time", "to_date", "to_time", "employee", "leave_type", "status"],
        order_by="from_date asc",
    )
    for employee in employees:
        employee.leaves = [leave for leave in leaves if leave.employee == employee.name]
        employee.holiday_weekdays = get_holiday_weekdays(employee.name, from_date, to_date)
    return employees


def get_leave_types():
    leave_types = frappe.db.get_all("Leave Dashboard Leave Types", fields=["leave_type", "color", "text"])
    for leave_type in leave_types:
        leave_type.className = to_valid_class_name(leave_type.leave_type)
    return leave_types


def get_holiday_lists(branches: set[str], from_date: date, to_date: date):
    from leave_dashboard.leave_dashboard.doctype.leave.leave import get_holidays

    holiday_lists = {}
    for branch_name in branches:
        holiday_lists[branch_name] = get_holidays(branch_name, from_date, to_date)
    return holiday_lists


def to_valid_class_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[\U0001F300-\U0001FAFF]", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    if re.match(r"^\d", text):
        text = f"_{text}"

    return text


def darken_color(hex_color, factor=0.7):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = [max(0, min(255, int(c * factor))) for c in (r, g, b)]
    return f"#{r:02x}{g:02x}{b:02x}"


def build_background_border_css(rules: list[dict]) -> str:
    css_lines = []
    for rule in rules:
        class_name = rule.get("className")
        color = rule.get("color")
        if not class_name or not color or not re.match(r"^#?[0-9a-fA-F]{6}$", color):
            continue

        base_color = f"#{color.lstrip('#')}"
        border_color = darken_color(base_color)

        css_lines.append(f".{class_name} {{")
        css_lines.append(f"  background-color: {base_color};")
        css_lines.append(f"  border-color: {border_color};")
        css_lines.append("}")
        css_lines.append("")
    return "\n".join(css_lines)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        from datetime import date, datetime

        if isinstance(obj, (date, datetime)):
            return obj.isoformat()

        if isinstance(obj, set):
            return self._convert_keys({item: True for item in obj})

        return super().default(obj)

    def encode(self, obj):
        obj = self._convert_keys(obj)
        return super().encode(obj)

    def _convert_keys(self, obj):
        from datetime import date, datetime

        if isinstance(obj, dict):
            new = {}
            for k, v in obj.items():
                if isinstance(k, (date, datetime)):
                    k = k.isoformat()
                new[k] = self._convert_keys(v)
            return new

        if isinstance(obj, list):
            return [self._convert_keys(i) for i in obj]

        return obj
