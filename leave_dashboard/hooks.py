app_name = "leave_dashboard"
app_title = "Leave Dashboard"
app_publisher = "david-loe"
app_description = "A quick view of who's off, when, and why."
app_email = "kontakt@david-loe.de"
app_license = "agpl-3.0"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "leave_dashboard",
# 		"logo": "/assets/leave_dashboard/logo.png",
# 		"title": "Leave Dashboard",
# 		"route": "/leave_dashboard",
# 		"has_permission": "leave_dashboard.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/leave_dashboard/css/leave_dashboard.css"
# app_include_js = "/assets/leave_dashboard/js/leave_dashboard.js"

# include js, css files in header of web template
# web_include_css = "/assets/leave_dashboard/css/leave_dashboard.css"
# web_include_js = "/assets/leave_dashboard/js/leave_dashboard.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "leave_dashboard/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Branch": "public/js/branch.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "leave_dashboard/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "leave_dashboard.utils.jinja_methods",
# 	"filters": "leave_dashboard.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "leave_dashboard.install.before_install"
# after_install = "leave_dashboard.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "leave_dashboard.uninstall.before_uninstall"
# after_uninstall = "leave_dashboard.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "leave_dashboard.utils.before_app_install"
# after_app_install = "leave_dashboard.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "leave_dashboard.utils.before_app_uninstall"
# after_app_uninstall = "leave_dashboard.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "leave_dashboard.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"leave_dashboard.tasks.all"
# 	],
# 	"daily": [
# 		"leave_dashboard.tasks.daily"
# 	],
# 	"hourly": [
# 		"leave_dashboard.tasks.hourly"
# 	],
# 	"weekly": [
# 		"leave_dashboard.tasks.weekly"
# 	],
# 	"monthly": [
# 		"leave_dashboard.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "leave_dashboard.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "leave_dashboard.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "leave_dashboard.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["leave_dashboard.utils.before_request"]
# after_request = ["leave_dashboard.utils.after_request"]

# Job Events
# ----------
# before_job = ["leave_dashboard.utils.before_job"]
# after_job = ["leave_dashboard.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"leave_dashboard.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "doctype": "Notification",
        "filters": [["name", "in", ["Leave Status Changed (DE)", "New Leave (DE)"]]],
    },
    {
        "doctype": "Workflow",
        "filters": [["name", "in", ["Leave Application"]]],
    },
    {
        "doctype": "Workflow Action Master",
        "filters": [["name", "in", ["Withdraw", "Submit"]]],
    },
    {
        "doctype": "Workflow State",
        "filters": [["name", "in", ["Cancelled", "Open"]]],
    },
    {
        "doctype": "Custom Field",
        "filters": [],
        "or_filters": [
            [
                "name",
                "in",
                [
                    "Leave Type-needs_approval",
                    "Employee-custom_section_break_hn48z",
                    "Employee-working_days",
                    "Employee-leave_policies",
                ],
            ],
            [
                "dt",
                "in",
                ["Branch"],
            ],
        ],
    },
]
