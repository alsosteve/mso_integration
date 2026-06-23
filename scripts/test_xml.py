# test pull xml capability

from pathlib import Path
import json
import requests

API_BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"

TARGET_NAME = "St Vincents East"
TARGET_CITY = "Birmingham"
TARGET_STATE = "AL"
TARGET_YEAR = 2022

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "test" / "xml_lookup"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_json(filename: str, payload: dict) -> None:
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved: {path}")


def find_match(name: str, city: str, state: str) -> dict | None:
    response = requests.get(
        f"{API_BASE_URL}/search.json",
        params={"q": name},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    save_json("search_response.json", data)

    organizations = data.get("organizations", [])
    if not organizations:
        return None

    # first pass: exact city/state
    for org in organizations:
        if (
            org.get("city", "").strip().upper() == city.upper()
            and org.get("state", "").strip().upper() == state.upper()
        ):
            return org

    # fallback: first result
    return organizations[0]


def get_org_record(ein: int) -> dict:
    response = requests.get(
        f"{API_BASE_URL}/organizations/{ein}.json",
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    save_json("organization_response.json", data)
    return data


def choose_filing(org_data: dict, target_year: int) -> dict | None:
    filings = org_data.get("filings_with_data", [])
    if not filings:
        return None

    for filing in filings:
        if filing.get("tax_prd_yr") == target_year:
            return filing

    # fallback: most recent available filing
    return filings[0]


def main() -> None:
    print("Searching for organization...")
    match = find_match(TARGET_NAME, TARGET_CITY, TARGET_STATE)

    if not match:
        print("No organization match found.")
        return

    print("\nMatched organization:")
    print("Name:", match.get("name"))
    print("EIN:", match.get("ein"))
    print("City:", match.get("city"))
    print("State:", match.get("state"))

    ein = match["ein"]

    print("\nPulling organization filing history...")
    org_data = get_org_record(ein)

    organization = org_data.get("organization", {})
    filings = org_data.get("filings_with_data", [])

    print("Organization name:", organization.get("name"))
    print("Total filings with data:", len(filings))

    chosen = choose_filing(org_data, TARGET_YEAR)
    if not chosen:
        print("No filing found.")
        return

    print("\nChosen filing:")
    print("Tax year:", chosen.get("tax_prd_yr"))
    print("Tax period:", chosen.get("tax_prd"))
    print("Form type:", chosen.get("formtype"))
    print("PDF URL:", chosen.get("pdf_url"))

    chosen_path = OUTPUT_DIR / "chosen_filing.json"
    chosen_path.write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    print(f"Saved: {chosen_path}")

    print("\nNext step:")
    print("Use the EIN + chosen filing year to look up the XML from your XML source.")


if __name__ == "__main__":
    main()