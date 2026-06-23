"""
This file randomly generates a sample of size 500 for unique ein's
in the hospital cros walk data.
"""

import json
from pathlib import Path

import pandas as pd


# project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CBI_FILE = PROJECT_ROOT / "cbi_hospitals_cleaned.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "output" / "ein_sample_500.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# Load CBI hospital crosswalk
with open(CBI_FILE, "r") as f:
    data = json.load(f)

df = pd.DataFrame(data)


# Clean EINs so they are stored as 9-digit strings
df["ein"] = (
    df["ein"]
    .astype(str)
    .str.replace(r"\D", "", regex=True)
    .str.zfill(9)
)

df = df[df["ein"].str.len() == 9]


# Group hospitals by EIN because Form 990 filings are organization/EIN-level,
# not always one filing per individual hospital
ein_frame = (
    df.groupby("ein")
      .agg(
          hospital_count=("hospital_id", "count"),
          hospital_names=("name", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
          states=("state", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
          medicare_provider_numbers=(
              "medicare_provider_number",
              lambda x: " | ".join(sorted(set(x.dropna().astype(str))))
          ),
      )
      .reset_index()
)


# Randomly sample 500 unique hospital-related EINs.
# random_state makes the sample reproducible.
sample_500 = ein_frame.sample(n=500, random_state=2026)


# Save sample for the next step
sample_500.to_csv(OUTPUT_FILE, index=False)


print("Done.")
print("Total unique hospital EINs:", len(ein_frame))
print("Sample size:", len(sample_500))
print("Saved file:", OUTPUT_FILE)
print(sample_500.head())