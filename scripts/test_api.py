# # testing api connection
# print("Start")
#
# from config import API_BASE_URL
# import requests
# import json
#
# url = f"{API_BASE_URL}/search.json?q=ST.%20VINCENTS%20EAST"
#
# response = requests.get(url)
# data = response.json()
#
# print(data.keys())
# print(data["organizations"][0].keys())
# print(json.dumps(data["organizations"][0], indent=2))
#
# # connect
# from config import API_BASE_URL
# import requests
#
# search_name = "ST. VINCENTS EAST"
# search_city = "BIRMINGHAM"
# search_state = "AL"
#
# # Step 1: search by hospital name
# search_response = requests.get(
#     f"{API_BASE_URL}/search.json",
#     params={"q": search_name}
# )
# search_data = search_response.json()
#
# print("Search status:", search_response.status_code)
# print("Total results:", search_data.get("total_results"))
#
# organizations = search_data.get("organizations", [])
#
# # Step 2: try to find a likely match by city/state
# match = None
# for org in organizations:
#     if (
#         org.get("city", "").upper() == search_city
#         and org.get("state", "").upper() == search_state
#     ):
#         match = org
#         break
#
# if not match:
#     print("No city/state match found.")
#     if organizations:
#         print("Closest returned orgs:")
#         for org in organizations[:5]:
#             print(org.get("name"), "-", org.get("city"), org.get("state"), "-", org.get("ein"))
#     raise SystemExit
#
# print("\nMatched organization:")
# print("Name:", match.get("name"))
# print("EIN:", match.get("ein"))
# print("City:", match.get("city"))
# print("State:", match.get("state"))
#
# ein = match["ein"]
#
# # Step 3: pull organization + filing data
# org_response = requests.get(f"{API_BASE_URL}/organizations/{ein}.json")
# org_data = org_response.json()
#
# print("\nOrganization endpoint status:", org_response.status_code)
#
# filings = org_data.get("filings_with_data", [])
# print("Number of filings with data:", len(filings))
#
# if not filings:
#     print("No filings_with_data found.")
#     raise SystemExit
#
# # Step 4: pick the most recent filing
# latest_filing = filings[0]
#
# print("\nMost recent filing:")
# print("Tax year:", latest_filing.get("tax_prd_yr"))
# print("Tax period:", latest_filing.get("tax_prd"))
# print("PDF URL:", latest_filing.get("pdf_url"))

from config import API_BASE_URL
import requests

search_name = "ST. VINCENTS EAST"
search_city = "BIRMINGHAM"
search_state = "AL"

# Step 1: search by hospital name
search_response = requests.get(
    f"{API_BASE_URL}/search.json",
    params={"q": search_name}
)
search_data = search_response.json()

print("Search status:", search_response.status_code)
print("Total results:", search_data.get("total_results"))

organizations = search_data.get("organizations", [])

# Step 2: try to find a likely match by city/state
match = None
for org in organizations:
    if (
        org.get("city", "").upper() == search_city
        and org.get("state", "").upper() == search_state
    ):
        match = org
        break

if not match:
    print("No city/state match found.")
    if organizations:
        print("Closest returned orgs:")
        for org in organizations[:5]:
            print(org.get("name"), "-", org.get("city"), org.get("state"), "-", org.get("ein"))
    raise SystemExit

print("\nMatched organization:")
print("Name:", match.get("name"))
print("EIN:", match.get("ein"))
print("City:", match.get("city"))
print("State:", match.get("state"))

ein = match["ein"]

# Step 3: pull organization + filing data
org_response = requests.get(f"{API_BASE_URL}/organizations/{ein}.json")
org_data = org_response.json()

print("\nOrganization endpoint status:", org_response.status_code)

filings = org_data.get("filings_with_data", [])

print("\nAll filings:")
for filing in filings:
    print(
        "Year:", filing.get("tax_prd_yr"),
        "| Tax period:", filing.get("tax_prd"),
        "| PDF URL:", filing.get("pdf_url")
    )

first_pdf = None
for filing in filings:
    if filing.get("pdf_url"):
        first_pdf = filing
        break

if first_pdf:
    print("\nFirst filing with a PDF:")
    print("Year:", first_pdf.get("tax_prd_yr"))
    print("Tax period:", first_pdf.get("tax_prd"))
    print("PDF URL:", first_pdf.get("pdf_url"))
else:
    print("\nNo filings with a PDF URL were found.")
print("Number of filings with data:", len(filings))

if not filings:
    print("No filings_with_data found.")
    raise SystemExit

# Step 4: pick the most recent filing
latest_filing = filings[0]

print("\nMost recent filing:")
print("Tax year:", latest_filing.get("tax_prd_yr"))
print("Tax period:", latest_filing.get("tax_prd"))
print("PDF URL:", latest_filing.get("pdf_url"))