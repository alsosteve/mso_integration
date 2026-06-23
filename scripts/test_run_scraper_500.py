"""
Run the IRS 990 XML scraper on the downloaded 500-sample XML files.

This script:
1. Reads XML files from data/raw/xml_500.
2. Extracts organization name, tax year, delegation status, relevant management text, and possible MSO name.
3. Saves scraper results to data/output/scraper_results_500.csv.

OG code context:
The previous student's scraper parsed IRS 990 XML files, searched management-related text,
and output fields like hospital/organization name, tax year, delegation status, MSO name,
relevant text, and extraction status.

OG code adjusted here:
This version runs on our newly downloaded XML sample instead of the old manually curated XML folder.
It also keeps source tracking fields like EIN, object_id, XML filename, and download-log metadata.
"""

import re
from pathlib import Path

import pandas as pd
from lxml import etree


# Set project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

XML_INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "xml_500"
DOWNLOAD_LOG = PROJECT_ROOT / "data" / "output" / "xml_download_log_500.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "output" / "scraper_results_500.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# Management/MSO keywords used to find relevant text blocks.
# OG code adjusted here:
# Kept the old keyword idea, but centralized the keywords so they are easy to edit later.
MANAGEMENT_KEYWORDS = [
    "managed by",
    "management services",
    "management service",
    "management agreement",
    "management contract",
    "administrative services",
    "administrative service",
    "services agreement",
    "contracted management",
    "delegation of management",
    "management duties",
    "managerial services",
    "management company",
    "management organization",
    "management services organization",
    "mso",
]


# Terms that commonly create false positives.
# OG code adjusted here:
# Added a simple noise filter so board/governance language does not get treated as MSO evidence.
NOISE_TERMS = [
    "board of directors",
    "board member",
    "board members",
    "governance",
    "investment management",
    "risk management",
    "case management",
    "care management",
    "pain management",
    "disease management",
]


def get_text_first(root, tag_name):
    """
    Find the first text value for an XML tag, ignoring namespaces.
    """
    values = root.xpath(f"//*[local-name()='{tag_name}']/text()")
    values = [v.strip() for v in values if v and v.strip()]
    return values[0] if values else ""


def get_all_text_for_tags(root, tag_names):
    """
    Pull text from a list of XML tag names, ignoring namespaces.
    """
    texts = []

    for tag in tag_names:
        values = root.xpath(f"//*[local-name()='{tag}']/text()")
        for value in values:
            value = value.strip()
            if value:
                texts.append(value)

    return texts


def clean_text(text):
    """
    Normalize spacing so text snippets are easier to read.
    """
    return re.sub(r"\s+", " ", text).strip()


def is_relevant_management_text(text):
    """
    Decide whether a text block looks relevant to MSO/management extraction.
    """
    lower = text.lower()

    has_keyword = any(keyword in lower for keyword in MANAGEMENT_KEYWORDS)
    has_noise = any(noise in lower for noise in NOISE_TERMS)

    return has_keyword and not has_noise


def extract_possible_mso_name(text):
    """
    Try to extract a likely management/MSO entity name from relevant text.

    This is still rule-based and imperfect.
    It should be treated as a first-pass extraction, not final truth.
    """
    patterns = [
        r"managed by ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"management services (?:are|were)? provided by ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"administrative services (?:are|were)? provided by ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"entered into (?:a|an) management agreement with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"management agreement with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"services agreement with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
        r"contracted with ([A-Z][A-Za-z0-9&,\.\- ]{3,120})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            possible_name = clean_text(match.group(1))

            # Stop extraction before common sentence endings.
            possible_name = re.split(
                r"\b(to|for|under|pursuant|which|that|and provides|and performs)\b",
                possible_name,
                flags=re.IGNORECASE,
            )[0]

            possible_name = possible_name.strip(" .,-;:")

            if len(possible_name) >= 3:
                return possible_name

    return ""


def parse_filename_metadata(xml_path):
    """
    Our downloaded XML filenames look like:
    EIN_TAXPERIOD_OBJECTID.xml

    Example:
    123456789_202412_202503219349309990.xml
    """
    parts = xml_path.stem.split("_")

    if len(parts) >= 3:
        return {
            "ein": parts[0],
            "tax_period_from_filename": parts[1],
            "object_id": parts[2],
        }

    return {
        "ein": "",
        "tax_period_from_filename": "",
        "object_id": "",
    }


def extract_990_data(xml_path):
    """
    Extract management/MSO-related fields from one IRS 990 XML file.
    """
    filename_meta = parse_filename_metadata(xml_path)

    try:
        parser = etree.XMLParser(recover=True, huge_tree=True)
        tree = etree.parse(str(xml_path), parser)
        root = tree.getroot()

    except Exception as e:
        return {
            **filename_meta,
            "xml_file": str(xml_path),
            "filing_organization_name": "",
            "tax_year": "",
            "tax_period_end": "",
            "delegation_of_management_duties": "",
            "possible_mso_name": "",
            "relevant_text": "",
            "extraction_status": "XML Parse Error",
            "error": str(e),
        }

    # Basic filing metadata
    organization_name = (
        get_text_first(root, "BusinessNameLine1Txt")
        or get_text_first(root, "BusinessNameLine1")
        or get_text_first(root, "Name")
    )

    tax_year = get_text_first(root, "TaxYr")
    tax_period_end = get_text_first(root, "TaxPeriodEndDt")

    # Delegation of management duties field
    delegation = get_text_first(root, "DelegationOfMgmtDutiesInd")

    # OG code adjusted here:
    # The old description focused on Schedule O and fallback narrative fields.
    # This pulls common narrative/explanation tags across the XML so we do not miss text
    # when IRS schema names vary by year.
    narrative_tags = [
        "ExplanationTxt",
        "Desc",
        "Description",
        "SupplementalInformationDetail",
        "FormAndLineReferenceDesc",
        "ReturnReference",
        "IdentifierReturnReference",
        "BusinessNameLine1Txt",
        "BusinessNameLine2Txt",
    ]

    all_text_blocks = get_all_text_for_tags(root, narrative_tags)

    relevant_blocks = []
    possible_mso_names = []

    for text in all_text_blocks:
        text = clean_text(text)

        if is_relevant_management_text(text):
            relevant_blocks.append(text)

            possible_name = extract_possible_mso_name(text)
            if possible_name:
                possible_mso_names.append(possible_name)

    # Remove duplicate relevant snippets while preserving order
    relevant_blocks = list(dict.fromkeys(relevant_blocks))
    possible_mso_names = list(dict.fromkeys(possible_mso_names))

    if possible_mso_names:
        extraction_status = "Exact MSO Match"
    elif relevant_blocks:
        extraction_status = "Relevant Text Found"
    else:
        extraction_status = "No Relevant Text Found"

    return {
        **filename_meta,
        "xml_file": str(xml_path),
        "filing_organization_name": organization_name,
        "tax_year": tax_year,
        "tax_period_end": tax_period_end,
        "delegation_of_management_duties": delegation,
        "possible_mso_name": " | ".join(possible_mso_names),
        "relevant_text": " || ".join(relevant_blocks),
        "extraction_status": extraction_status,
        "error": "",
    }


# Run scraper on downloaded XML files
xml_files = sorted(XML_INPUT_DIR.glob("*.xml"))

print("XML files found:", len(xml_files))
print("Input folder:", XML_INPUT_DIR)

results = []

for xml_file in xml_files:
    print("Scraping:", xml_file.name)
    results.append(extract_990_data(xml_file))

results_df = pd.DataFrame(results)


# OG code adjusted here:
# Merge scraper results back to the download log so each row keeps source/download context.
if DOWNLOAD_LOG.exists() and not results_df.empty:
    log_df = pd.read_csv(DOWNLOAD_LOG, dtype=str)

    if "object_id" in log_df.columns and "object_id" in results_df.columns:
        results_df = results_df.merge(
            log_df[
                [
                    "object_id",
                    "irs_index_year",
                    "taxpayer_name",
                    "status",
                    "hospital_count",
                    "hospital_names",
                    "states",
                    "medicare_provider_numbers",
                ]
            ],
            on="object_id",
            how="left",
            suffixes=("", "_download_log"),
        )


results_df.to_csv(OUTPUT_FILE, index=False)

print()
print("Done.")
print("Rows scraped:", len(results_df))
print("Output saved to:", OUTPUT_FILE)

if not results_df.empty:
    print()
    print("Extraction status counts:")
    print(results_df["extraction_status"].value_counts())
