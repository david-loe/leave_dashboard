// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Branch", {
	refresh(frm) {
		frappe.call({
			method: "leave_dashboard.leave_dashboard.utils.get_supported_countries",
			callback(r) {
				if (!r.message) return;

				frm.subdivisions_by_country = r.message.subdivisions_by_country;

				frm.fields_dict.country.set_data(
					r.message.countries.sort((a, b) => a.label.localeCompare(b.label))
				);

				if (frm.doc.country) {
					frm.trigger("set_subdivisions");
				}
			},
		});
	},
	country: function (frm) {
		frm.set_value("subdivision", "");

		if (frm.doc.country) {
			frm.trigger("set_subdivisions");
		}
	},
	set_subdivisions: function (frm) {
		const subdivisions = [...frm.subdivisions_by_country[frm.doc.country]];
		if (subdivisions && subdivisions.length > 0) {
			frm.fields_dict.subdivision.set_data(subdivisions);
			frm.set_df_property("subdivision", "hidden", 0);
		} else {
			frm.fields_dict.subdivision.set_data([]);
			frm.set_df_property("subdivision", "hidden", 1);
		}
	},
});
