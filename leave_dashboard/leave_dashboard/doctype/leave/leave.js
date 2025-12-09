// Copyright (c) 2025, david-loe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave", {
    setup: function (frm) {
        frm.set_query("leave_approver", function () {
            return {
                query: "hrms.hr.doctype.department_approver.department_approver.get_approvers",
                filters: {
                    employee: frm.doc.employee,
                    doctype: "Leave Application",
                },
            };
        });
        frm.set_query("employee", erpnext.queries.employee);

    },
    onload: function (frm) {
        if (!frm.doc.posting_date) {
            frm.set_value("posting_date", frappe.datetime.get_today());
        }
        frm.trigger("get_needs_approval");
    },
    refresh: function (frm) {
        frm.trigger("set_employee");
        frm.trigger("set_date_picker_limits");
        frm.trigger("make_dashboard");
    },
    async set_employee(frm) {
        if (!frm.doc.employee && frm.doc.docstatus == 0) {
            const employee = await hrms.get_current_employee(frm);
            if (employee) {
                frm.set_value("employee", employee);
            }
        }
    },
    employee: function (frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("set_leave_approver");
        frm.trigger("make_dashboard");
    },
    leave_type: function (frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("get_needs_approval");
    },
    from_date: function (frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("set_date_picker_limits");
    },
    from_time: function (frm) {
        frm.trigger("calculate_total_days");
    },
    to_date: function (frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("set_date_picker_limits");
    },
    to_time: function (frm) {
        frm.trigger("calculate_total_days");
    },
    set_date_picker_limits: function (frm) {
        if (frm.doc.docstatus == 0) {
            // set minimum To Date equal to From Date
            frm.fields_dict.to_date.datepicker.update({
                minDate: frm.doc.from_date ? new Date(frm.doc.from_date) : null
            });
            // set maximum From Date equal to To Date
            frm.fields_dict.from_date.datepicker.update({
                maxDate: frm.doc.to_date ? new Date(frm.doc.to_date) : null
            });
        }
    },
    calculate_total_days: function (frm) {
        if (frm.doc.docstatus == 0 && frm.doc.employee && frm.doc.leave_type && frm.doc.from_date && frm.doc.from_time && frm.doc.to_date && frm.doc.to_time) {
            // server call is done to include holidays in leave days calculations
            return frappe.call({
                method: "leave_dashboard.leave_dashboard.doctype.leave.leave.get_number_of_leave_days",
                args: {
                    employee: frm.doc.employee,
                    leave_type: frm.doc.leave_type,
                    from_date: frm.doc.from_date,
                    from_time: frm.doc.from_time,
                    to_date: frm.doc.to_date,
                    to_time: frm.doc.to_time,
                },
                callback: function (r) {
                    if (r && r.message !== undefined) {
                        frm.set_value("total_leave_days", r.message);
                        frm.trigger("get_leave_balance");
                    }
                },
            });
        }
    },
    get_needs_approval: function (frm) {
        if (frm.doc.docstatus == 0 && frm.doc.leave_type) {
            return frappe.call({
                method: "leave_dashboard.leave_dashboard.doctype.leave.leave.get_needs_approval",
                args: {
                    leave_type: frm.doc.leave_type,
                },
                callback: function (r) {
                    if (r) {
                        frm.toggle_reqd("leave_approver", r.message);
                        frm.toggle_display("leave_approver", r.message)
                    }
                },
            });
        }
    },
    set_leave_approver: function (frm) {
        if (frm.doc.docstatus == 0 && frm.doc.employee) {
            return frappe.call({
                method: "hrms.hr.doctype.leave_application.leave_application.get_leave_approver",
                args: {
                    employee: frm.doc.employee,
                },
                callback: function (r) {
                    if (r && r.message) {
                        frm.set_value("leave_approver", r.message);
                    }
                },
            });
        }
    },
    make_dashboard: async function (frm) {
        if (frm.doc.employee && frm.doc.docstatus == 0) {
            leave_balances = (await frappe.call({
                method: "leave_dashboard.leave_dashboard.doctype.leave.leave.get_leave_balance_overview",
                args: {
                    employee: frm.doc.employee,
                }
            })).message

            $("div").remove(".form-dashboard-section.custom");

            frm.dashboard.add_section(
                frappe.render_template("leave_balance_overview", {
                    leave_balances,
                }),
                __("Allocated Leaves"),
            );
            frm.dashboard.show();
        }
    },
});
