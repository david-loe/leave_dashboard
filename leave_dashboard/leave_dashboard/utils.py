import frappe
	
@frappe.whitelist()
def get_supported_countries():
    from holidays.utils import list_supported_countries

    subdivisions_by_country = list_supported_countries()
    countries = [
        {"value": country, "label": local_country_name(country)}
        for country in subdivisions_by_country.keys()
    ]
    return {
        "countries": countries,
        "subdivisions_by_country": subdivisions_by_country,
    }

def local_country_name(country_code: str) -> str:
	"""Return the localized country name for the given country code."""
	from babel import Locale

	return Locale.parse(frappe.local.lang, sep="-").territories.get(country_code, country_code)
