# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from datetime import datetime,timedelta,date
import frappe
from frappe import _
import json

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
        
    context.current_user = frappe.get_doc("User", frappe.session.user)
    
    roles = frappe.get_roles()
    if "Employee" not in roles:
        frappe.throw("Not permitted", frappe.PermissionError)
        
    settings = frappe.get_single("Leave Dashboard Settings")
    
    today = datetime.today()
    from_date = today - timedelta(days=settings.data_days_in_past)
    to_date = today + timedelta(days=settings.data_days_in_future)
    
    context.settings_json = json.dumps(settings.as_dict(), cls=DateTimeEncoder)
    leave_data = get_leave_data(from_date, to_date)
    unique_holiday_lists = set(emp['holiday_list'] for emp in leave_data)
    context.leave_data_json = json.dumps(leave_data, cls=DateTimeEncoder)
    context.holiday_lists_json = json.dumps(get_holiday_lists(unique_holiday_lists, from_date, to_date), cls=DateTimeEncoder)
    leave_types = get_leave_types()
    context.leave_types_json = json.dumps(leave_types)
    leave_types.append({"className": "default-leave", "color": settings.default_leave_color})
    context.leave_types_css = build_background_border_css(leave_types)
    context.button_text = _('Add') + ' ' + _('Leave Application')



def get_leave_data(from_date: datetime , to_date: datetime):
    employees = frappe.db.get_all("Employee", filters={"status": "Active", 'holiday_list': ["is", "set"]}, fields=['name','first_name', 'last_name','holiday_list','employee_name', 'user_id' ], order_by="last_name asc")
    applications = frappe.db.get_all("Leave Application", filters={"status": "Approved", "to_date": [">=", from_date.strftime("%Y-%m-%d")], "from_date": ["<=", to_date.strftime("%Y-%m-%d")]}, fields=['from_date', 'to_date', 'employee', 'leave_type', 'half_day', 'half_day_date'], order_by="from_date asc")
    for employee in employees:
        employee.leaves = [leave for leave in applications if leave.employee == employee.name]
    return employees


def get_leave_types():
    leave_types = frappe.db.get_all("Leave Dashboard Leave Types", fields=["leave_type", "color", "text"])
    for leave_type in leave_types:
        leave_type.className = to_valid_class_name(leave_type.leave_type)
    return leave_types

def get_holiday_lists(lists: set[str], from_date: date, to_date:date):
    holiday_lists = {}
    for list_name in lists:
        holidays = frappe.db.get_all("Holiday", filters= {"parent": list_name, "holiday_date": ["Between", [from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")]]}, fields=['holiday_date', 'description'], order_by="holiday_date asc")
        holiday_lists[list_name] = holidays
    return holiday_lists


import re
import unicodedata

def to_valid_class_name(text: str) -> str:
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[\U0001F300-\U0001FAFF]', '', text)
    text = re.sub(r'[^\w\s-]', '', text)
    text = text.lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = text.strip('-')
    if re.match(r'^\d', text):
        text = f'_{text}'

    return text

def darken_color(hex_color, factor=0.7):
    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = [max(0, min(255, int(c * factor))) for c in (r, g, b)]
    return f"#{r:02x}{g:02x}{b:02x}"

def build_background_border_css(rules: list[dict]) -> str:
    css_lines = []
    for rule in rules:
        class_name = rule.get("className")
        color = rule.get("color")
        if not class_name or not color or not re.match(r'^#?[0-9a-fA-F]{6}$', color):
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
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)