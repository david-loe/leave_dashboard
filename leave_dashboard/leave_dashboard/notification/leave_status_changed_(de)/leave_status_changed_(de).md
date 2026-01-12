{% set from_date_str = frappe.utils.getdate(doc.from_date).strftime("%-d.%-m.") %}
{% set to_date_str   = frappe.utils.getdate(doc.to_date).strftime("%-d.%-m.%Y") %}

<h3>Antrag auf {{ doc.leave_type }} {{ doc.status }}</h3>
<p>
Dein Antrag auf {{ doc.leave_type }}
für den Zeitraum <strong>{{ from_date_str }} – {{ to_date_str }}</strong> 
wurde <strong>{{ doc.status }}</strong>.
</p>
{% if doc.status == "Rejected" %}
<p>
  Bitte wende dich bei Rückfragen an {{ doc.leave_approver }}.
</p>
{% endif %}
<p style="text-align: center; margin-top: 20px;">
<a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}"
   style="display: inline-block; background-color: #fa8c16; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 15px;">
  Details & Status prüfen
</a>
</p>
<p>Hier kommst du zur <a href="{{frappe.utils.get_url()}}/leave_dashboard">Urlaubsübersicht</a>.</p>
