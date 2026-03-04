"""
Generate curated source URLs from templates and overrides.
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ISIN-based URL templates (validated to work)
ISIN_TEMPLATES = [
    "https://www.justetf.com/de/etf-profile.html?isin={ISIN}",
    "https://extraetf.com/de/etf-profile/{ISIN}",
    "https://www.finanzfluss.de/informer/etf/{isin_lower}/",
    "https://www.comdirect.de/inf/etfs/{ISIN}",
    "https://www.avl-investmentfonds.de/fonds/details/{ISIN}"
]


def load_overrides(overrides_path: str = "src/source_overrides.json") -> Dict[str, List[str]]:
    """Load hardcoded URL overrides from JSON file."""
    if not os.path.exists(overrides_path):
        logger.warning(f"Overrides file not found: {overrides_path}")
        return {}

    with open(overrides_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_sources(isins: List[str], output_path: str = "outputs/sources.json") -> Dict:
    """
    Generate curated source URLs for each ISIN.
    Returns dict: {isin: {timestamp, urls}}
    """
    sources = {}
    overrides = load_overrides()

    for isin in isins:
        urls = []

        # Add ISIN-based template URLs
        for template in ISIN_TEMPLATES:
            url = template.format(ISIN=isin, isin_lower=isin.lower())
            urls.append(url)

        # Add hardcoded overrides
        if isin in overrides:
            urls.extend(overrides[isin])

        sources[isin] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "urls": urls
        }

        logger.info(f"Generated {len(urls)} URLs for {isin}")

    # Save to file
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)

    logger.info(f"Sources saved to {output_path}")
    return sources


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate curated source URLs")
    parser.add_argument("--isins", default="LU3098954871,LU3075459852", help="Comma-separated ISINs")
    parser.add_argument("--output", default="outputs/sources.json", help="Output JSON file")
    args = parser.parse_args()

    isins = [isin.strip() for isin in args.isins.split(',')]
    generate_sources(isins, args.output)
