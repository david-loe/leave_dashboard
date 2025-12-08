# Copyright (c) 2025, david-loe and contributors
# For license information, please see license.txt

import datetime
from dateutil.relativedelta import relativedelta
from typing import Literal, TypedDict
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Order
from hrms.hr.utils import validate_active_employee
from frappe.utils import (
    DateTimeLikeObject,
    cint,
    date_diff,
    formatdate,
    get_link_to_form,
    getdate,
    now_datetime,
)


class OverlapError(frappe.ValidationError):
    pass


class InsufficientLeaveBalanceError(frappe.ValidationError):
    pass


class Leave(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        employee: DF.Link
        from_date: DF.Date
        from_time: DF.Literal["Morning", "Noon"]
        leave_approver: DF.Link | None
        leave_type: DF.Link
        posting_date: DF.Date
        reason: DF.SmallText | None
        status: DF.Literal["Open", "Approved", "Rejected", "Cancelled"]
        to_date: DF.Date
        to_time: DF.Literal["Noon", "Evening"]
        total_leave_days: DF.Float
    # end: auto-generated types

    def validate(self):
        validate_active_employee(self.employee)
        self.validate_dates()
        self.validate_approver()
        self.validate_leave_overlap()
        self.validate_enough_leave_balance()
        self.set_total_leave_days()

    def on_update(self):
        self.auto_approve_and_submit()

    def validate_dates(self):
        if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
            frappe.throw(_("To date cannot be before from date"))
        if (
            self.from_date
            and self.to_date
            and (getdate(self.to_date) == getdate(self.from_date))
            and self.from_time == "Noon"
            and self.to_time == "Noon"
        ):
            frappe.throw(_("To and from date cannot be the same and both on noon"))

    def validate_approver(self):
        if get_needs_approval(self.leave_type):
            if not self.leave_approver:
                frappe.throw((_("Leave Approver is Mandatory for {0}").format(self.leave_type)), frappe.MandatoryError)
        else:
            self.leave_approver = None

    def auto_approve_and_submit(self):
        if self.docstatus == 0 and self.status == "Open" and not get_needs_approval(self.leave_type):
            from frappe.model.workflow import apply_workflow

            apply_workflow(self, "Submit")

    def validate_leave_overlap(self):
        if not self.name:
            # hack! if name is null, it could cause problems with !=
            self.name = "New Leave Application"
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        Leave = frappe.qb.DocType("Leave")

        start_cond = (
            (Leave.from_date <= to_date)
            if self.to_time == "Evening"
            else (Leave.from_date < to_date) | ((Leave.from_date == to_date) & (Leave.from_time == "Morning"))
        )
        end_cond = (
            (Leave.to_date >= from_date)
            if self.from_time == "Morning"
            else (Leave.to_date > from_date) | ((Leave.to_date == from_date) & (Leave.to_time == "Evening"))
        )

        query = (
            frappe.qb.from_(Leave)
            .select(Leave.name, Leave.leave_type, Leave.from_date, Leave.to_date)
            .where(Leave.employee == self.employee)
            .where((Leave.status.isin(["Open", "Approved"])) & (Leave.docstatus < 2))
            .where(Leave.name != self.name)
            .where(start_cond)
            .where(end_cond)
        )

        for overlap_leave in query.run(as_dict=True):
            form_link = get_link_to_form("Leave", overlap_leave.name)
            msg = _("Employee {0} has already applied for {1} between {2} and {3} : {4}").format(
                self.employee,
                overlap_leave["leave_type"],
                formatdate(overlap_leave["from_date"]),
                formatdate(overlap_leave["to_date"]),
                form_link,
            )
            frappe.throw(msg, OverlapError)

    def validate_enough_leave_balance(self):
        if (
            self.status == "Rejected"
            or self.status == "Cancelled"
            or frappe.db.get_value("Leave Type", self.leave_type, "allow_negative")
        ):
            return
        leave_parts = split_into_periods(getdate(self.from_date), self.from_time, getdate(self.to_date), self.to_time)
        for part in leave_parts:
            balance = get_leave_balance(self.employee, part["period"][0], part["period"][1], self.leave_type)[
                self.leave_type
            ]["balance"]
            if not self.name:
                balance -= get_number_of_leave_days(self.employee, self.leave_type, **part["leave"])
            if balance < 0:
                msg = _("Employee {0} does not have enough leave balance ({1}) for {2} in period {3} - {4}.").format(
                    self.employee,
                    balance,
                    self.leave_type,
                    formatdate(part["period"][0]),
                    formatdate(part["period"][1]),
                )
                frappe.throw(msg, InsufficientLeaveBalanceError)

    def set_total_leave_days(self):
        self.total_leave_days = get_number_of_leave_days(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=self.from_date,
            from_time=self.from_time,
            to_date=self.to_date,
            to_time=self.to_time,
        )


def on_doctype_update():
    frappe.db.add_index("Leave Application", ["employee", "from_date", "to_date"])


@frappe.whitelist()
def get_needs_approval(leave_type: str):
    return bool(frappe.db.get_value("Leave Type", leave_type, "needs_approval"))


@frappe.whitelist()
def get_number_of_leave_days(
    employee: str,
    leave_type: str,
    from_date: DateTimeLikeObject,
    from_time: Literal["Morning", "Noon"],
    to_date: DateTimeLikeObject,
    to_time: Literal["Noon", "Evening"],
    **kwags,
) -> float:
    """Returns number of leave days between 2 dates after considering time and holidays
    (Based on the include_holiday setting in Leave Type)"""
    start = getdate(from_date)
    end = getdate(to_date)
    number_of_days = date_diff(end, start) + 1
    if number_of_days < 1:
        return 0
    if from_time == "Noon":
        number_of_days -= 0.5
    if to_time == "Noon":
        number_of_days -= 0.5

    if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
        number_of_days = number_of_days - get_number_of_holidays(employee, start, from_time, end, to_time)

    return number_of_days


@frappe.whitelist()
def get_leave_balance_overview(employee: str, date: DateTimeLikeObject | None = None):
    period_start, period_end = get_period(getdate(date) if date else now_datetime().date())
    return get_leave_balance(employee, period_start, period_end, None)


def get_number_of_holidays(
    employee: str,
    from_date: datetime.date,
    from_time: Literal["Morning", "Noon"],
    to_date: datetime.date,
    to_time: Literal["Noon", "Evening"],
) -> float:
    """Returns number of holidays between 2 dates"""

    holidays = get_holidays_for_employee(employee, from_date, to_date)
    holiday_weekdays = get_holiday_weekdays(employee, from_date, to_date)
    count = 0

    def getDayLength(day: datetime.date):
        if day == from_date and from_time == "Noon":
            return 0.5
        if day == to_date and to_time == "Noon":
            return 0.5
        return 1

    def getHolidayAmount(
        day: datetime.date,
        custom_holiday_time: Literal["Morning -> Evening", "Morning -> Noon", "Noon -> Evening"] | None,
    ):
        if not custom_holiday_time or custom_holiday_time == "Morning -> Evening":
            return getDayLength(day)
        elif custom_holiday_time == "Morning -> Noon":
            if day == from_date and from_time == "Noon":
                return 0
            return 0.5
        elif custom_holiday_time == "Noon -> Evening":
            if day == to_date and to_time == "Noon":
                return 0
            return 0.5

    day = from_date
    while day <= to_date:
        if day in holiday_weekdays:
            count += getDayLength(day)
        elif day in holidays["country_holidays"]:
            count += getDayLength(day)
        elif day in holidays["custom_holidays"]:
            count += getHolidayAmount(day, holidays["custom_holidays"][day]["time"])
        day += datetime.timedelta(days=1)

    return count


def get_holidays_for_employee(employee: str, from_date: datetime.date, to_date: datetime.date):
    branch_name = frappe.db.get_value("Employee", employee, "branch")
    return get_holidays(branch_name, from_date, to_date)


def get_holidays(branch_name: str | None, from_date: datetime.date, to_date: datetime.date):
    result = {"country_holidays": {}, "custom_holidays": {}}

    if branch_name:
        branch = frappe.db.get_value("Branch", branch_name, ["country", "subdivision"], as_dict=True)
        if branch:
            years = range(from_date.year, to_date.year + 1)
            if branch["country"]:
                from holidays import country_holidays

                result["country_holidays"] = country_holidays(
                    country=branch["country"], subdiv=branch["subdivision"], language=frappe.local.lang, years=years
                )

            custom_holidays = frappe.db.get_all(
                "Custom Holiday",
                filters={"parent": branch_name, "parenttype": "Branch"},
                fields=["date", "label", "time"],
            )

            for holiday in custom_holidays:
                for year in years:
                    result["custom_holidays"][holiday.date.replace(year=year)] = holiday

    return result


def get_holiday_weekdays(employee: str, from_date: datetime.date, to_date: datetime.date):
    Working_Days = frappe.qb.DocType("Working Days")

    working_days_rules = (
        frappe.qb.from_(Working_Days)
        .select(Working_Days.star)
        .where(Working_Days.parent == employee)
        .where(Working_Days.parenttype == "Employee")
        .where(Working_Days.parentfield == "working_days")
        .where(Working_Days.valid_from <= to_date)
        .orderby(Working_Days.valid_from, order=Order.desc)
    ).run(as_dict=True)

    rules = []
    weekday_keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    found_rule_before_from_date = False
    for rule in working_days_rules:
        holiday_weekdays = {0, 1, 2, 3, 4, 5, 6}
        for i, key in enumerate(weekday_keys):
            if rule[key] == 1:
                holiday_weekdays.discard(i)
        rules.append({"valid_from": rule["valid_from"], "holiday_weekdays": holiday_weekdays})
        found_rule_before_from_date = rule["valid_from"] <= from_date
        if found_rule_before_from_date:
            break

    if not found_rule_before_from_date:
        branch_name = frappe.db.get_value("Employee", employee, "branch")
        default_holiday_weekdays = get_default_holiday_weekdays(branch_name)
        rules.append({"valid_from": from_date, "holiday_weekdays": default_holiday_weekdays})

    holidays: set[datetime.date] = set()
    r_index = 0
    r_len = len(rules)
    day = to_date
    while day >= from_date:
        while r_index < r_len and rules[r_index]["valid_from"] > day:
            r_index += 1
        if day.weekday() in rules[r_index]["holiday_weekdays"]:
            holidays.add(day)
        day -= datetime.timedelta(days=1)

    return holidays


def get_leave_balance(
    employee: str,
    period_start: datetime.date,
    period_end: datetime.date,
    leave_type: str | None,
    is_carry_forward_child=False,
):
    result = {}
    allocations = get_number_of_allocated_leaves(
        employee, period_start, period_end, leave_type, not is_carry_forward_child
    )
    for leave_type_key in allocations:
        result[leave_type_key] = {
            "allocated": allocations[leave_type_key],
            "balance": allocations[leave_type_key],
            "taken": 0,
            "taken_from_prev": None,
        }

    taken = get_number_of_taken_leaves(employee, period_start, period_end, leave_type)
    for leave_type_key in taken:
        if leave_type_key not in result:
            result[leave_type_key] = {"allocated": 0, "balance": 0, "taken": 0, "taken_from_prev": None}
        result[leave_type_key]["taken"] = taken[leave_type_key]["total"]
        result[leave_type_key]["balance"] = result[leave_type_key]["allocated"] - result[leave_type_key]["taken"]

    for leave_type_key in result:
        is_carry_forward, maximum_carry_forwarded_leaves = frappe.db.get_value(
            "Leave Type", leave_type_key, ["is_carry_forward", "maximum_carry_forwarded_leaves"]
        )
        if is_carry_forward and result[leave_type_key]["allocated"] != 0:
            period_length = cint(frappe.db.get_single_value("Leave Settings", "period_length"), 12)
            number_of_leaves_prev_not_taken = max(
                get_leave_balance(
                    employee,
                    period_start - relativedelta(months=period_length),
                    period_end - relativedelta(months=period_length),
                    leave_type_key,
                    True,
                )[leave_type_key]["balance"],
                0,
            )
            if maximum_carry_forwarded_leaves:
                number_of_leaves_prev_not_taken = min(maximum_carry_forwarded_leaves, number_of_leaves_prev_not_taken)
            taken_from_type = taken.get(leave_type_key, {"possible_carry_forward": 0, "total": 0})
            result[leave_type_key]["taken_from_prev"] = min(
                number_of_leaves_prev_not_taken,
                (
                    taken_from_type["possible_carry_forward"]
                    if taken_from_type["possible_carry_forward"] is not None
                    else taken_from_type["total"]
                ),
            )
            result[leave_type_key]["balance"] = result[leave_type_key]["allocated"] - (
                result[leave_type_key]["taken"] - result[leave_type_key]["taken_from_prev"]
            )

    return result


def get_number_of_taken_leaves(
    employee: str, period_start: datetime.date, period_end: datetime.date, leave_type: str | None
):
    def get_number_of_days_in_period(leave_list: list[dict], p_start: datetime.date, p_end: datetime.date) -> float:
        total = 0
        # trim to period
        for leave in leave_list:
            trimmed = False
            if leave["from_date"] > p_end or leave["to_date"] < p_start:
                continue
            if leave["from_date"] < p_start:
                leave["from_date"] = p_start
                leave["from_time"] = "Morning"
                trimmed = True
            if leave["to_date"] > p_end:
                leave["to_date"] = p_end
                leave["to_time"] = "Evening"
                trimmed = True
            # only recalc trimmed leaves
            if trimmed:
                leave["total_leave_days"] = get_number_of_leave_days(**leave)
            total += leave["total_leave_days"]
        return total

    Leave = frappe.qb.DocType("Leave")
    baseQ = Leave.employee == employee
    if leave_type:
        baseQ = baseQ & (Leave.leave_type == leave_type)
    leaves = (
        frappe.qb.from_(Leave)
        .select(
            Leave.total_leave_days,
            Leave.employee,
            Leave.leave_type,
            Leave.from_date,
            Leave.from_time,
            Leave.to_date,
            Leave.to_time,
        )
        .where(baseQ)
        .where(Leave.from_date <= period_end)
        .where(Leave.to_date >= period_start)
        .where((Leave.status.isin(["Open", "Approved"])) & (Leave.docstatus < 2))
        .run(as_dict=True)
    )

    by_type = {}
    if leave_type:
        by_type[leave_type] = leaves
    else:
        for leave in leaves:
            lt = leave["leave_type"]
            if lt not in by_type:
                by_type[lt] = []
            by_type[lt].append(leave)

    result: dict[str, dict[str, float | None]] = {}
    for type, leave_list in by_type.items():
        result[type] = {"total": 0.0, "possible_carry_forward": None}
        result[type]["total"] = get_number_of_days_in_period(leave_list, period_start, period_end)

        is_carry_forward, expire_carry_forwarded_leaves_after_days = frappe.db.get_value(
            "Leave Type", type, ["is_carry_forward", "expire_carry_forwarded_leaves_after_days"]
        )
        if is_carry_forward and expire_carry_forwarded_leaves_after_days:
            result[type]["possible_carry_forward"] = get_number_of_days_in_period(
                leave_list,
                period_start,
                period_start + datetime.timedelta(days=expire_carry_forwarded_leaves_after_days),
            )

    return result


def get_number_of_allocated_leaves(
    employee: str, period_start: datetime.date, period_end: datetime.date, leave_type: str | None, allocate_if_not=True
):
    Employee_Leave_Policies = frappe.qb.DocType("Employee Leave Policies")
    Leave_Policy_Detail = frappe.qb.DocType("Leave Policy Detail")
    baseQ = Leave_Policy_Detail.parenttype == "Leave Policy"
    if leave_type:
        baseQ = baseQ & (Leave_Policy_Detail.leave_type == leave_type)
    leave_policy_rules = (
        frappe.qb.from_(Employee_Leave_Policies)
        .join(Leave_Policy_Detail)
        .on(Employee_Leave_Policies.leave_policy == Leave_Policy_Detail.parent)
        .select(
            Employee_Leave_Policies.valid_from, Leave_Policy_Detail.leave_type, Leave_Policy_Detail.annual_allocation
        )
        .where(baseQ)
        .where(Employee_Leave_Policies.parent == employee)
        .where(Employee_Leave_Policies.parenttype == "Employee")
        .where(Employee_Leave_Policies.parentfield == "leave_policies")
        .where(Employee_Leave_Policies.valid_from <= period_end)
        .orderby(Employee_Leave_Policies.valid_from, order=Order.desc)
    ).run(as_dict=True)

    sums = {}
    period_length = cint(frappe.db.get_single_value("Leave Settings", "period_length"), 12)
    last_valid_from = None
    for rule in leave_policy_rules:
        if last_valid_from and last_valid_from > rule["valid_from"]:
            break
        amount = rule["annual_allocation"]
        lp_p_start, lp_p_end = get_period(rule["valid_from"])
        if lp_p_start != rule["valid_from"]:
            amount = rule["annual_allocation"] * (
                (period_length - months_between(lp_p_start, rule["valid_from"])) / period_length
            )

        leave_type = rule["leave_type"]
        sums[leave_type] = sums.get(leave_type, 0) + amount

        if rule["valid_from"] <= period_start:
            last_valid_from = rule["valid_from"]

    return sums


def get_default_holiday_weekdays(branch: str):
    is_working_day = frappe.db.get_value(
        "Branch", branch, ["dwd_mon", "dwd_tue", "dwd_wed", "dwd_thu", "dwd_fri", "dwd_sat", "dwd_sun"]
    )
    holiday_weekdays = {0, 1, 2, 3, 4, 5, 6}
    for i in range(0, 7):
        if is_working_day[i] == 1:
            holiday_weekdays.discard(i)
    return holiday_weekdays


def get_period(date: datetime.date, period_offset: int = 0):
    period_start = frappe.db.get_single_value("Leave Settings", "period_start")
    period_length = cint(frappe.db.get_single_value("Leave Settings", "period_length"), 12)

    normalized_start = datetime.date(date.year - 1, period_start.month, period_start.day)
    # Compute how many months passed since this normalized start
    diff_years = date.year - normalized_start.year
    diff_months = diff_years * 12 + date.month - normalized_start.month

    # Determine the period index after normalization
    period_index = diff_months // period_length

    # Calculate actual period start and end
    period_start = normalized_start + relativedelta(months=(period_index + period_offset) * period_length)
    period_end = period_start + relativedelta(months=period_length) - relativedelta(days=1)

    return period_start, period_end


class LeaveSpan(TypedDict):
    from_date: datetime.date
    from_time: Literal["Morning", "Noon"]
    to_date: datetime.date
    to_time: Literal["Noon", "Evening"]


class LeavePart(TypedDict):
    leave: LeaveSpan
    period: tuple[datetime.date, datetime.date]


def split_into_periods(
    from_date: datetime.date,
    from_time: Literal["Morning", "Noon"],
    to_date: datetime.date,
    to_time: Literal["Noon", "Evening"],
):
    period_start, period_end = get_period(from_date)
    parts: list[LeavePart] = [
        {
            "leave": {"from_date": from_date, "from_time": from_time, "to_date": period_end, "to_time": "Evening"},
            "period": (period_start, period_end),
        }
    ]
    index = 1
    while period_end < to_date:
        period_start, period_end = get_period(from_date, index)
        parts.append(
            {
                "leave": {
                    "from_date": period_start,
                    "from_time": "Morning",
                    "to_date": period_end,
                    "to_time": "Evening",
                },
                "period": (period_start, period_end),
            }
        )
        index += 1
    parts[-1]["leave"].update({"to_date": to_date, "to_time": to_time})
    return parts


def months_between(d1: datetime.date, d2: datetime.date):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)
