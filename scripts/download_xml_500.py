"""
Download actual IRS XML files for the 500 sampled hospital-related EINs.

This script:
1. Reads xml_matches_500.csv.
2. Keeps the most recent Form 990 filing for each EIN.
3. Downloads IRS ZIP files that contains those XML filings.
4. Extracts matching XML files using the IRS object_id.
5. Saves a download log showing what worked and what failed.

Store into raw folder.
"""
"""
Important:
- This script keeps a log at xml_download_log_500.csv.
- It will be skipp filings already logged on future runs.
- This prevents the same failed downloads.

Start with TEST_LIMIT = 10 while testing.
After the script success verification, change TEST_LIMIT to None.
"""

import ssl
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd


# Set project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

MATCHES_FILE = PROJECT_ROOT / "data" / "output" / "xml_matches_500.csv"
XML_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "xml_500"
ZIP_CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "irs_zips"
LOG_FILE = PROJECT_ROOT / "data" / "output" / "xml_download_log_500.csv"

XML_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ZIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# Test mode: only try this many filings per run.
# Change to None when ready to process everything remaining.
TEST_LIMIT = 10


def get_zip_urls(year):
    """
    Return possible IRS ZIP URLs for a given IRS index year.

    Older years use names like download990xml_2019_1.zip.
    Newer years use names like 2024_TEOS_XML_01A.zip.
    """
    base = f"https://apps.irs.gov/pub/epostcard/990/xml/{year}"

    if year in [2019, 2020]:
        urls = [f"{base}/{year}_TEOS_XML_CT1.zip"]
        urls += [f"{base}/download990xml_{year}_{i}.zip" for i in range(1, 9)]
        return urls

    if year in [2021, 2022]:
        return [f"{base}/{year}_TEOS_XML_01A.zip"]

    if year in [2023, 2024]:
        return [f"{base}/{year}_TEOS_XML_{month:02d}A.zip" for month in range(1, 13)]

    if year == 2025:
        urls = [f"{base}/{year}_TEOS_XML_{month:02d}A.zip" for month in range(1, 13)]
        urls += [
            f"{base}/{year}_TEOS_XML_05B.zip",
            f"{base}/{year}_TEOS_XML_11B.zip",
            f"{base}/{year}_TEOS_XML_11C.zip",
            f"{base}/{year}_TEOS_XML_11D.zip",
        ]
        return urls

    if year == 2026:
        return [f"{base}/{year}_TEOS_XML_{month:02d}A.zip" for month in range(1, 6)]

    return []


def download_zip(url):
    """
    Download a ZIP file if it is not already saved locally.
    """
    zip_name = url.split("/")[-1]
    zip_path = ZIP_CACHE_DIR / zip_name

    if zip_path.exists():
        return zip_path, "already_downloaded"

    try:
        context = ssl._create_unverified_context()

        print(f"Downloading ZIP: {zip_name}")
        with urllib.request.urlopen(url, context=context) as response:
            zip_path.write_bytes(response.read())

        return zip_path, "downloaded"

    except Exception as e:
        return None, f"zip_download_failed: {e}"


def extract_xml_from_zip(zip_path, object_id, output_name):
    """
    Look inside a ZIP file for an XML whose filename contains the object_id.
    If found, extract it to XML_OUTPUT_DIR.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                member_name = Path(member).name

                if object_id in member_name and member_name.endswith(".xml"):
                    output_path = XML_OUTPUT_DIR / output_name

                    try:
                        with z.open(member) as source:
                            output_path.write_bytes(source.read())

                        return output_path, member_name

                    except NotImplementedError as e:
                        print(f"Unsupported compression for {member_name} in {zip_path.name}: {e}")
                        return None, None

                    except Exception as e:
                        print(f"Could not extract {member_name} from {zip_path.name}: {e}")
                        return None, None

        return None, None

    except Exception as e:
        print(f"Could not open ZIP {zip_path.name}: {e}")
        return None, None


# Load IRS index matches
df = pd.read_csv(MATCHES_FILE, dtype=str)

# Keep regular Form 990 filings only
df = df[df["return_type"] == "990"].copy()

# Clean tax_period so newer filings sort correctly
df["tax_period_num"] = pd.to_numeric(df["tax_period"], errors="coerce")

# Keep the most recent filing per EIN
latest = (
    df.sort_values(["ein", "tax_period_num", "irs_index_year"])
      .groupby("ein", as_index=False)
      .tail(1)
      .copy()
)


# Skip filings that were already attempted in a previous run.
# This includes both successful downloads and failures.
if LOG_FILE.exists():
    old_log = pd.read_csv(LOG_FILE, dtype=str)
    already_tried = set(old_log["object_id"].dropna().astype(str))

    before = len(latest)
    latest = latest[~latest["object_id"].astype(str).isin(already_tried)].copy()
    after = len(latest)

    print(f"Skipped already logged filings: {before - after}")


if TEST_LIMIT is not None:
    latest = latest.head(TEST_LIMIT).copy()

print("Filings selected for XML download:", len(latest))


log_rows = []

for _, row in latest.iterrows():
    ein = row["ein"]
    object_id = row["object_id"]
    irs_index_year = int(row["irs_index_year"])
    tax_period = row["tax_period"]
    taxpayer_name = row["taxpayer_name"]

    output_name = f"{ein}_{tax_period}_{object_id}.xml"

    print()
    print(f"Looking for XML: EIN={ein}, tax_period={tax_period}, object_id={object_id}")

    found_xml_path = None
    found_zip_name = None
    status = "xml_not_found"

    zip_urls = get_zip_urls(irs_index_year)

    for url in zip_urls:
        zip_path, zip_status = download_zip(url)

        if zip_path is None:
            continue

        extracted_path, xml_member_name = extract_xml_from_zip(
            zip_path=zip_path,
            object_id=object_id,
            output_name=output_name,
        )

        if extracted_path is not None:
            found_xml_path = extracted_path
            found_zip_name = zip_path.name
            status = "downloaded"
            print(f"Found XML in {found_zip_name}")
            break

    log_rows.append({
        "ein": ein,
        "tax_period": tax_period,
        "irs_index_year": irs_index_year,
        "taxpayer_name": taxpayer_name,
        "object_id": object_id,
        "xml_file": str(found_xml_path) if found_xml_path else "",
        "zip_file": found_zip_name if found_zip_name else "",
        "status": status,
        "hospital_count": row.get("hospital_count", ""),
        "hospital_names": row.get("hospital_names", ""),
        "states": row.get("states", ""),
        "medicare_provider_numbers": row.get("medicare_provider_numbers", ""),
    })


# Append new results to the existing log instead of overwriting it.
new_log = pd.DataFrame(log_rows)

if LOG_FILE.exists():
    old_log = pd.read_csv(LOG_FILE, dtype=str)
    log = pd.concat([old_log, new_log], ignore_index=True)
else:
    log = new_log

log.to_csv(LOG_FILE, index=False)


print()
print("Done.")
print("XML files saved in:", XML_OUTPUT_DIR)
print("Download log saved to:", LOG_FILE)

if not log.empty:
    print()
    print("Overall log status counts:")
    print(log["status"].value_counts())

if not new_log.empty:
    print()
    print("This run status counts:")
    print(new_log["status"].value_counts())