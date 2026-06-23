import ssl
import urllib.request
from io import StringIO
from pathlib import Path

import pandas as pd


# Set project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

SAMPLE_FILE = PROJECT_ROOT / "data" / "output" / "ein_sample_500.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "output" / "xml_matches_500.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# IRS index years to search.
# These are filing/submission years, so we search multiple years.
INDEX_YEARS = list(range(2019, 2027))


# Load 500 sampled hospital-related EINs
sample = pd.read_csv(SAMPLE_FILE)

sample["ein"] = (
    sample["ein"]
    .astype(str)
    .str.replace(r"\D", "", regex=True)
    .str.zfill(9)
)

sample_eins = set(sample["ein"])

print("Loaded EIN sample:", len(sample_eins))


all_matches = []

for year in INDEX_YEARS:
    index_url = f"https://apps.irs.gov/pub/epostcard/990/xml/{year}/index_{year}.csv"

    print()
    print("Reading IRS index:", year)
    print(index_url)

    try:
        # Mac/Python sometimes has IRS SSL certificate issues.
        # This reads the IRS CSV while bypassing that local certificate problem.
        context = ssl._create_unverified_context()

        with urllib.request.urlopen(index_url, context=context) as response:
            csv_text = response.read().decode("utf-8", errors="replace")

        idx = pd.read_csv(StringIO(csv_text), dtype=str)

    except Exception as e:
        print("Could not read this index:", e)
        continue

    # Clean column names so matching is easier
    idx.columns = idx.columns.str.strip().str.lower()

    if "ein" not in idx.columns:
        print("No EIN column found. Skipping this year.")
        print("Columns found:", list(idx.columns))
        continue

    # Clean IRS EINs to same 9-digit format
    idx["ein"] = (
        idx["ein"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(9)
    )

    # Keep only IRS rows where EIN is in our 500-sample
    matches = idx[idx["ein"].isin(sample_eins)].copy()

    if matches.empty:
        print("Matches found: 0")
        continue

    matches["irs_index_year"] = year
    all_matches.append(matches)

    print("Matches found:", len(matches))


if not all_matches:
    print()
    print("No XML matches found.")
else:
    xml_matches = pd.concat(all_matches, ignore_index=True)

    # Add hospital info from the 500-sample to the IRS match rows
    xml_matches = xml_matches.merge(
        sample,
        on="ein",
        how="left",
        suffixes=("_irs", "_sample")
    )

    xml_matches.to_csv(OUTPUT_FILE, index=False)

    print()
    print("Done.")
    print("Total IRS filing matches:", len(xml_matches))
    print("Unique sampled EINs with IRS match:", xml_matches["ein"].nunique())
    print("Saved file:", OUTPUT_FILE)
    print()
    print(xml_matches.head())