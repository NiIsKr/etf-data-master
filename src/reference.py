"""
Extract ground truth ETF name and TER from factsheet PDFs.
"""
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from pypdf import PdfReader
except ImportError:
    print("ERROR: pypdf not installed. Run: pip install pypdf")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Canonical names (fallback if PDF parsing fails)
CANONICAL_NAMES = {
    "LU3098954871": "TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc)",
    "LU3075459852": "Inyova Impact Investing Active Equity Fund UCITS ETF EUR"
}

# Manual TER override (fallback if PDF parsing fails)
TER_OVERRIDES = {
    "LU3098954871": 0.69  # TEQ TER hardcoded as specified
}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""


def extract_name_from_text(text: str, isin: str) -> Optional[str]:
    """
    Extract ETF name from PDF text.
    Looks for common patterns like "Name:", "Fondname:", etc.
    """
    # Common patterns for ETF name in factsheets
    patterns = [
        r"(?:Name|Fondname|Fondsname|Fund Name|ETF Name)[\s:]+([^\n]{10,150})",
        r"(?:Bezeichnung)[\s:]+([^\n]{10,150})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up common artifacts
            name = re.sub(r'\s+', ' ', name)
            if len(name) > 10:  # Sanity check
                logger.info(f"Extracted name from PDF: {name}")
                return name

    logger.warning(f"Could not extract name from PDF, using canonical name for {isin}")
    return CANONICAL_NAMES.get(isin)


def extract_ter_from_text(text: str, isin: str) -> Optional[float]:
    """
    Extract TER from PDF text.
    Looks for keywords like "TER", "Total Expense Ratio", "Laufende Kosten", etc.
    """
    # Keywords that indicate TER
    keywords = [
        "TER", "Total Expense Ratio", "Gesamtkostenquote",
        "laufende Kosten", "Kostenquote", "Ongoing Charges"
    ]

    # Search for TER near keywords
    for keyword in keywords:
        # Find keyword position
        keyword_pos = text.lower().find(keyword.lower())
        if keyword_pos == -1:
            continue

        # Extract context around keyword (100 chars)
        context_start = max(0, keyword_pos - 50)
        context_end = min(len(text), keyword_pos + 100)
        context = text[context_start:context_end]

        # Look for percentage pattern
        ter_pattern = r'(\d+[.,]\d{1,4})\s*%'
        matches = re.findall(ter_pattern, context)

        if matches:
            # Take first match, normalize decimal separator
            ter_str = matches[0].replace(',', '.')
            ter_value = float(ter_str)

            # Sanity check (TER should be between 0.01% and 5%)
            if 0.01 <= ter_value <= 5.0:
                logger.info(f"Extracted TER from PDF: {ter_value}%")
                return ter_value

    # Check for manual override
    if isin in TER_OVERRIDES:
        logger.warning(f"Could not extract TER from PDF, using manual override: {TER_OVERRIDES[isin]}%")
        return TER_OVERRIDES[isin]

    logger.error(f"Could not extract TER from PDF for {isin}")
    return None


def extract_reference(inputs_dir: str = "inputs", output_path: str = "outputs/reference.json") -> Dict:
    """
    Extract ground truth from PDFs in inputs directory.
    Returns dict: {isin: {name, ter, source}}
    """
    reference = {}

    # Map ISINs to PDF filenames
    pdf_map = {
        "LU3098954871": "FS_LU3098954871_de.pdf",
        "LU3075459852": "fwwdok_dxjMduzPQS.pdf"
    }

    for isin, pdf_filename in pdf_map.items():
        pdf_path = os.path.join(inputs_dir, pdf_filename)

        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            # Use fallbacks
            name = CANONICAL_NAMES.get(isin)
            ter = TER_OVERRIDES.get(isin)

            if name and ter:
                reference[isin] = {
                    "name": name,
                    "ter": ter,
                    "source": f"fallback (PDF missing: {pdf_filename})"
                }
                logger.warning(f"Using fallback data for {isin}")
            else:
                logger.error(f"No fallback data available for {isin}")
            continue

        logger.info(f"Processing {pdf_path}...")
        text = extract_text_from_pdf(pdf_path)

        if not text:
            logger.error(f"No text extracted from {pdf_path}")
            continue

        # Extract name and TER
        name = extract_name_from_text(text, isin)
        ter = extract_ter_from_text(text, isin)

        if name and ter:
            reference[isin] = {
                "name": name,
                "ter": ter,
                "source": pdf_filename
            }
            logger.info(f"✅ {isin}: {name} | TER: {ter}%")
        else:
            logger.error(f"Failed to extract complete data from {pdf_path}")

    # Save to file
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(reference, f, indent=2, ensure_ascii=False)

    logger.info(f"Reference data saved to {output_path}")
    return reference


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract ground truth from ETF factsheets")
    parser.add_argument("--inputs-dir", default="inputs", help="Directory containing PDF files")
    parser.add_argument("--output", default="outputs/reference.json", help="Output JSON file")
    args = parser.parse_args()

    extract_reference(args.inputs_dir, args.output)
