"""
Run the original-style IRS 990 XML scraper on the downloaded sample XML files.

This script follows the previous student's scraper structure:
1. Parse IRS Form 990 XML files.
2. Extract basic filing metadata.
3. Search narrative text for management/MSO-related language.
4. Extract a possible MSO or management entity name.
5. Save a structured CSV output.

Only adjustment:
- Original code was adjusted here to read XMLs from data/raw/xml_500
  instead of the previous manually curated "XML Files" folder.
- Original code was adjusted here to save output as sample_scraper_results.csv.
"""

import re
from pathlib import Path

import pandas as pd
from lxml import etree


# Original code was adjusted here:
# Use the XMLs downloaded by download_xml_500.py.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
XML_FOLDER = PROJECT_ROOT / "data" / "raw" / "xml_500"

# Original code was adjusted here:
# Save this sample scrape separately from the old student's combined output.
OUTPUT_FILE = PROJECT_ROOT / "data" / "output" / "sample_scraper_results.csv"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


MANAGEMENT_KEYWORDS = [
    "managed by",
    "management services",
    "administrative services",
    "management agreement",
    "services agreement",
    "contracted management duties",
    "delegation of management duties",
    "management company",
    "management organization",
    "management services organization",
    "mso",
]


NOISE_TERMS = [
    "board of directors",
    "board members",
    "governance",
    "investment management",
    "risk management",
    "case management",
    "care management",
    "pain management",
    "disease management",
]


def first_text(root, tag_name):
    """Return the first text value for a tag, ignoring XML namespaces."""
    values = root.xpath(f"//*[local-name()='{tag_name}']/text()")
    values = [v.strip() for v in values if v and v.strip()]
    return values[0] if values else ""


def all_text(root, tag_names):
    """Return all text values from selected tags, ignoring XML namespaces."""
    texts = []

    for tag_name in tag_names:
        values = root.xpath(f"//*[local-name()='{tag_name}']/text()")

        for value in values:
            value = value.strip()
            if value:
                texts.append(value)

    return texts


def clean_text(text):
    """Clean spacing in extracted text."""
    return re.sub(r"\s+", " ", text).strip()


def is_relevant_text(text):
    """Check whether text contains management language and avoids obvious noise."""
    lower = text.lower()

    has_keyword = any(keyword in lower for keyword in MANAGEMENT_KEYWORDS)
    has_noise = any(noise in lower for noise in NOISE_TERMS)

    return has_keyword and not has_noise


def extract_mso_name(text):
    """
    Extract a possible MSO/management entity name from relevant text.
    This follows the original rule-based/regex approach.
    """
    patterns = [
        r"managed by ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"management services (?:are|were)? provided by ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"administrative services (?:are|were)? provided by ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"management agreement with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"services agreement with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"contracted with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            name = clean_text(match.group(1))

            # Stop before common continuation words.
            name = re.split(
                r"\b(to|for|under|pursuant|which|that|and)\b",
                name,
                flags=re.IGNORECASE,
            )[0]

            name = name.strip(" .,-;:")

            if len(name) >= 3:
                return name

    return ""


def extract_990_data(xml_file):
    """Extract original-style MSO fields from one XML filing."""
    try:
        parser = etree.XMLParser(recover=True, huge_tree=True)
        tree = etree.parse(str(xml_file), parser)
        root = tree.getroot()

    except Exception as e:
        return {
            "Hospital Name": "",
            "Year": "",
            "Delegation of Management Duties Indicator": "",
            "MSO Name": "",
            "Relevant Text Block": "",
            "Extraction Status": "XML Parse Error",
            "Source XML": xml_file.name,
            "Error": str(e),
        }

    hospital_name = (
        first_text(root, "BusinessNameLine1Txt")
        or first_text(root, "BusinessNameLine1")
        or first_text(root, "Name")
    )

    year = first_text(root, "TaxYr") or first_text(root, "TaxPeriodEndDt")

    delegation_indicator = first_text(root, "DelegationOfMgmtDutiesInd")

    # Original code searched narrative/supporting text sections such as Schedule O
    # and fallback narrative fields.
    narrative_tags = [
        "ExplanationTxt",
        "Desc",
        "Description",
        "SupplementalInformationDetail",
        "FormAndLineReferenceDesc",
    ]

    text_blocks = all_text(root, narrative_tags)

    relevant_texts = []
    mso_names = []

    for text in text_blocks:
        text = clean_text(text)

        if is_relevant_text(text):
            relevant_texts.append(text)

            mso_name = extract_mso_name(text)
            if mso_name:
                mso_names.append(mso_name)

    relevant_texts = list(dict.fromkeys(relevant_texts))
    mso_names = list(dict.fromkeys(mso_names))

    if mso_names:
        status = "Exact MSO Match"
    elif relevant_texts:
        status = "Relevant Text Found"
    else:
        status = "No Relevant Text Found"

    return {
        "Hospital Name": hospital_name,
        "Year": year,
        "Delegation of Management Duties Indicator": delegation_indicator,
        "MSO Name": " | ".join(mso_names),
        "Relevant Text Block": " || ".join(relevant_texts),
        "Extraction Status": status,
        "Source XML": xml_file.name,
        "Error": "",
    }


results = []

xml_files = sorted(XML_FOLDER.glob("*.xml"))

print("XML folder:", XML_FOLDER)
print("XML files found:", len(xml_files))

for xml_file in xml_files:
    print("Processing:", xml_file.name)
    results.append(extract_990_data(xml_file))


results_df = pd.DataFrame(results)
results_df.to_csv(OUTPUT_FILE, index=False)

print()
print("Done.")
print("Rows processed:", len(results_df))
print("Output saved to:", OUTPUT_FILE)

if not results_df.empty:
    print()
    print("Extraction status counts:")
    print(results_df["Extraction Status"].value_counts())