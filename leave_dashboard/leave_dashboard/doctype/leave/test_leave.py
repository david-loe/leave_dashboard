# Copyright (c) 2025, david-loe and Contributors
# See license.txt

import datetime
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from leave_dashboard.leave_dashboard.doctype.leave import leave


class _DummyDocType:
	def __init__(self, table: str):
		self.table = table

	def __getattr__(self, item: str):
		return f"{self.table}.{item}"


class _DummyQuery:
	def __init__(self, data):
		self.data = data

	def select(self, *args, **kwargs):
		return self

	def where(self, *args, **kwargs):
		return self

	def join(self, *args, **kwargs):
		return self

	def on(self, *args, **kwargs):
		return self

	def run(self, as_dict=False):
		return self.data


class TestLeave(FrappeTestCase):
	def test_get_number_of_leave_days_accounts_for_half_days_and_holidays(self):
		employee = "EMP-001"
		leave_type = "Annual"
		from_date = datetime.date(2025, 1, 1)
		to_date = datetime.date(2025, 1, 3)

		with patch.object(leave.frappe.db, "get_value", return_value=0) as mock_get_value, patch.object(
			leave, "get_number_of_holidays", return_value=0.5
		) as mock_get_holidays:
			days = leave.get_number_of_leave_days(
				employee=employee,
				leave_type=leave_type,
				from_date=from_date,
				from_time="Noon",
				to_date=to_date,
				to_time="Noon",
			)

		self.assertEqual(days, 1.5)
		mock_get_value.assert_called_once_with("Leave Type", leave_type, "include_holiday")
		mock_get_holidays.assert_called_once_with(employee, from_date, "Noon", to_date, "Noon")

	def test_get_number_of_leave_days_respects_include_holiday_flag(self):
		employee = "EMP-002"
		leave_type = "Special"
		from_date = datetime.date(2025, 2, 10)
		to_date = datetime.date(2025, 2, 12)

		with patch.object(leave.frappe.db, "get_value", return_value=1), patch.object(
			leave, "get_number_of_holidays"
		) as mock_get_holidays:
			days = leave.get_number_of_leave_days(
				employee=employee,
				leave_type=leave_type,
				from_date=from_date,
				from_time="Noon",
				to_date=to_date,
				to_time="Noon",
			)

		self.assertEqual(days, 2)
		mock_get_holidays.assert_not_called()

	def test_get_number_of_holidays_counts_partial_days(self):
		employee = "EMP-003"
		from_date = datetime.date(2025, 1, 1)
		to_date = datetime.date(2025, 1, 3)
		holiday_dates = {datetime.date(2025, 1, 2), datetime.date(2025, 1, 3)}

		with patch.object(leave, "get_holidays", return_value=holiday_dates), patch.object(
			leave, "get_holiday_weekdays", return_value={2}
		):
			count = leave.get_number_of_holidays(employee, from_date, "Noon", to_date, "Noon")

		self.assertEqual(count, 2.0)

	def test_split_into_periods_spans_multiple_periods(self):
		from_date = datetime.date(2025, 1, 10)
		to_date = datetime.date(2025, 3, 5)
		period_map = {
			0: (datetime.date(2025, 1, 1), datetime.date(2025, 1, 31)),
			1: (datetime.date(2025, 2, 1), datetime.date(2025, 2, 28)),
			2: (datetime.date(2025, 3, 1), datetime.date(2025, 3, 31)),
		}

		def fake_get_period(_date, period_offset=0):
			return period_map[period_offset]

		with patch.object(leave, "get_period", side_effect=fake_get_period):
			parts = leave.split_into_periods(from_date, "Noon", to_date, "Noon")

		self.assertEqual(len(parts), 3)

		first, second, third = parts

		self.assertEqual(first["period"], period_map[0])
		self.assertEqual(first["leave"]["from_date"], from_date)
		self.assertEqual(first["leave"]["from_time"], "Noon")
		self.assertEqual(first["leave"]["to_date"], period_map[0][1])
		self.assertEqual(first["leave"]["to_time"], "Evening")

		self.assertEqual(second["period"], period_map[1])
		self.assertEqual(second["leave"]["from_date"], period_map[1][0])
		self.assertEqual(second["leave"]["from_time"], "Morning")
		self.assertEqual(second["leave"]["to_date"], period_map[1][1])
		self.assertEqual(second["leave"]["to_time"], "Evening")

		self.assertEqual(third["period"], period_map[2])
		self.assertEqual(third["leave"]["from_date"], period_map[2][0])
		self.assertEqual(third["leave"]["from_time"], "Morning")
		self.assertEqual(third["leave"]["to_date"], to_date)
		self.assertEqual(third["leave"]["to_time"], "Noon")

	def test_get_leave_balance_without_carry_forward_delegates_directly(self):
		leave_type_doc = {
			"is_carry_forward": 0,
			"maximum_carry_forwarded_leaves": 0,
			"expire_carry_forwarded_leaves_after_days": None,
			"name": "Annual",
		}
		employee = "EMP-004"
		period_start = datetime.date(2025, 4, 1)
		period_end = datetime.date(2025, 4, 30)
		expected = {"balance": 7}

		with patch.object(leave.frappe.db, "get_value", return_value=leave_type_doc) as mock_get_value, patch.object(
			leave.frappe.db, "get_single_value"
		) as mock_get_single_value, patch.object(leave, "_get_leave_balance", return_value=expected) as mock_get_balance:
			result = leave.get_leave_balance(employee, leave_type_doc["name"], period_start, period_end)

		self.assertEqual(result, expected)
		mock_get_value.assert_called_once_with(
			"Leave Type",
			leave_type_doc["name"],
			["is_carry_forward", "maximum_carry_forwarded_leaves", "expire_carry_forwarded_leaves_after_days", "name"],
			as_dict=True,
		)
		mock_get_single_value.assert_not_called()
		mock_get_balance.assert_called_once_with(employee, leave_type_doc, period_start, period_end)

	def test_get_leave_balance_with_carry_forward_fetches_period_length(self):
		leave_type_doc = {
			"is_carry_forward": 1,
			"maximum_carry_forwarded_leaves": 5,
			"expire_carry_forwarded_leaves_after_days": 30,
			"name": "Carry Forward",
		}
		employee = "EMP-005"
		period_start = datetime.date(2025, 5, 1)
		period_end = datetime.date(2025, 5, 31)

		with patch.object(leave.frappe.db, "get_value", return_value=leave_type_doc), patch.object(
			leave.frappe.db, "get_single_value", return_value=12
		) as mock_get_single_value, patch.object(
			leave, "_get_leave_balance", return_value={"balance": 10}
		) as mock_get_balance:
			result = leave.get_leave_balance(employee, leave_type_doc["name"], period_start, period_end)

		self.assertEqual(result, {"balance": 10})
		mock_get_single_value.assert_called_once_with("Leave Settings", "period_length")
		mock_get_balance.assert_called_once()
		args, _ = mock_get_balance.call_args
		self.assertEqual(args[0], employee)
		self.assertEqual(args[1], leave_type_doc)
		self.assertEqual(args[2], period_start)
		self.assertEqual(args[3], period_end)
		self.assertEqual(args[4], 12)

	def test__get_leave_balance_basic_no_carry_forward(self):
		leave_type = {
			"name": "Annual",
			"is_carry_forward": 0,
			"maximum_carry_forwarded_leaves": 0,
			"expire_carry_forwarded_leaves_after_days": None,
		}
		period_start = datetime.date(2025, 6, 1)
		period_end = datetime.date(2025, 6, 30)

		with patch.object(leave, "get_number_of_allocated_leaves", return_value=12) as mock_allocated, patch.object(
			leave, "get_number_of_taken_leaves", return_value={"total": 5}
		) as mock_taken:
			result = leave._get_leave_balance("EMP-200", leave_type, period_start, period_end)

		self.assertEqual(result["allocated"], 12)
		self.assertEqual(result["taken"], 5)
		self.assertEqual(result["balance"], 7)
		self.assertIsNone(result["taken_from_prev"])
		mock_allocated.assert_called_once_with("EMP-200", "Annual", period_start, period_end, True)
		mock_taken.assert_called_once_with("EMP-200", "Annual", period_start, period_end, None)

	def test__get_leave_balance_carry_forward_applies_previous_balance(self):
		leave_type = {
			"name": "Carry Forward",
			"is_carry_forward": 1,
			"maximum_carry_forwarded_leaves": 2,
			"expire_carry_forwarded_leaves_after_days": 15,
		}
		period_start = datetime.date(2025, 7, 1)
		period_end = datetime.date(2025, 7, 31)
		original = leave._get_leave_balance

		def fake_get_leave_balance(*args, **kwargs):
			is_child = kwargs.get("is_carry_forward_child")
			if is_child is None and len(args) >= 6:
				is_child = args[5]
			if is_child:
				return {"balance": 6}
			return original(*args, **kwargs)

		with patch.object(leave, "get_number_of_allocated_leaves", return_value=10), patch.object(
			leave, "get_number_of_taken_leaves", return_value={"total": 8, "possible_carry_forward": 3}
		), patch.object(leave, "_get_leave_balance", side_effect=fake_get_leave_balance):
			result = leave._get_leave_balance("EMP-201", leave_type, period_start, period_end, 12)

		self.assertEqual(result["taken_from_prev"], 2)
		self.assertEqual(result["balance"], 4)

	def test_get_number_of_taken_leaves_trims_and_counts_carry_forward(self):
		employee = "EMP-202"
		leave_type = "Annual"
		period_start = datetime.date(2025, 1, 1)
		period_end = datetime.date(2025, 1, 31)
		leaves_data = [
			{
				"employee": employee,
				"leave_type": leave_type,
				"from_date": datetime.date(2025, 1, 5),
				"from_time": "Morning",
				"to_date": datetime.date(2025, 1, 6),
				"to_time": "Evening",
				"total_leave_days": 2,
			},
			{
				"employee": employee,
				"leave_type": leave_type,
				"from_date": datetime.date(2024, 12, 30),
				"from_time": "Morning",
				"to_date": datetime.date(2025, 1, 2),
				"to_time": "Evening",
				"total_leave_days": 4,
			},
			{
				"employee": employee,
				"leave_type": leave_type,
				"from_date": datetime.date(2025, 1, 30),
				"from_time": "Morning",
				"to_date": datetime.date(2025, 2, 2),
				"to_time": "Evening",
				"total_leave_days": 4,
			},
			{
				"employee": employee,
				"leave_type": leave_type,
				"from_date": datetime.date(2025, 2, 5),
				"from_time": "Morning",
				"to_date": datetime.date(2025, 2, 6),
				"to_time": "Evening",
				"total_leave_days": 2,
			},
		]
		dummy_query = _DummyQuery([dict(leave) for leave in leaves_data])

		with patch.object(leave.frappe.qb, "DocType", side_effect=lambda name: _DummyDocType(name)), patch.object(
			leave.frappe.qb, "from_", return_value=dummy_query
		), patch.object(leave.frappe.db, "get_value", return_value=1):
			result = leave.get_number_of_taken_leaves(employee, leave_type, period_start, period_end, 5)

		self.assertEqual(result["total"], 6)
		self.assertEqual(result["possible_carry_forward"], 4)

	def test_get_number_of_allocated_leaves_sums_entries(self):
		employee = "EMP-203"
		leave_type = "Annual"
		period_start = datetime.date(2025, 2, 1)
		period_end = datetime.date(2025, 2, 28)
		dummy_query = _DummyQuery([(3,), (5,)])

		with patch.object(leave.frappe.qb, "DocType", side_effect=lambda name: _DummyDocType(name)), patch.object(
			leave.frappe.qb, "from_", return_value=dummy_query
		):
			result = leave.get_number_of_allocated_leaves(employee, leave_type, period_start, period_end)

		self.assertEqual(result, 8)

	def test_get_number_of_allocated_leaves_allocates_when_missing(self):
		employee = "EMP-204"
		leave_type = "Annual"
		period_start = datetime.date(2025, 3, 1)
		period_end = datetime.date(2025, 3, 31)
		dummy_query = _DummyQuery([])

		with patch.object(leave.frappe.qb, "DocType", side_effect=lambda name: _DummyDocType(name)), patch.object(
			leave.frappe.qb, "from_", return_value=dummy_query
		), patch.object(
			leave, "allocate_leaves", return_value={leave_type: 9}
		) as mock_allocate:
			result = leave.get_number_of_allocated_leaves(employee, leave_type, period_start, period_end)

		self.assertEqual(result, 9)
		mock_allocate.assert_called_once_with(employee, period_start, period_end, leave_type)

		with patch.object(leave.frappe.qb, "DocType", side_effect=lambda name: _DummyDocType(name)), patch.object(
			leave.frappe.qb, "from_", return_value=_DummyQuery([])
		), patch.object(leave, "allocate_leaves") as mock_allocate:
			result_without_allocate = leave.get_number_of_allocated_leaves(
				employee, leave_type, period_start, period_end, allocate_if_not=False
			)

		self.assertEqual(result_without_allocate, 0)
		mock_allocate.assert_not_called()
