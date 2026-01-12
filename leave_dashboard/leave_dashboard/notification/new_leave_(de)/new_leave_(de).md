{% set from_date_str = frappe.utils.getdate(doc.from_date).strftime("%-d.%-m.") %}
{% set to_date_str   = frappe.utils.getdate(doc.to_date).strftime("%-d.%-m.%Y") %}

<h3>Neuer Antrag auf {{ doc.leave_type }}</h3>
<p>
<strong>{{ doc.employee }}</strong> hat einen neuen Urlaubsantrag 
(<em>{{ doc.name }}</em>) eingereicht.
</p>
<ul>
<li>Zeitraum: {{ from_date_str }} – {{ to_date_str }}</li>
<li>Typ: {{ doc.leave_type }}</li>
<li>Anzahl Tage: {{ doc.total_leave_days }}</li>
{% if doc.reason %}
  <li>Grund: {{ doc.reason }}</li>
{% endif %}
</ul>
<p style="text-align: center; margin-top: 20px;">
<a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}"
   style="display: inline-block; background-color: #1890ff; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 15px;">
  Antrag jetzt prüfen
</a>
</p>
<p>Hier kommst du zur <a href="{{frappe.utils.get_url()}}/leave_dashboard">Urlaubsübersicht</a>.</p>
