# Copyright (c) 2025, david-loe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class WorkingDays(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fri: DF.Check
		mon: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sat: DF.Check
		sun: DF.Check
		thu: DF.Check
		tue: DF.Check
		valid_from: DF.Date
		wed: DF.Check
	# end: auto-generated types
	pass
