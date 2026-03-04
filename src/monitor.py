"""
Main orchestration module for ETF monitoring.
Auto-bootstraps reference and sources, then runs comparison.
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Import our modules
from . import reference, curated_sources, search_discovery, extract_web, llm_fallback, notify_slack

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize name for comparison: strip and collapse whitespace."""
    return ' '.join(name.strip().split())


def names_match(name1: str, name2: str) -> bool:
    """Check if two names match after normalization."""
    return normalize_name(name1) == normalize_name(name2)


def ters_match(ter1: float, ter2: float) -> bool:
    """Check if two TER values match (rounded to 4 decimals)."""
    return round(ter1, 4) == round(ter2, 4)


def compare_result(result: Dict, ref_name: str, ref_ter: float) -> str:
    """
    Compare extraction result with reference data.
    Returns status: MATCH, NAME_MISMATCH, TER_MISMATCH, BOTH_MISMATCH, TER_MISSING, FETCH_ERROR
    """
    if result.get('error'):
        return 'FETCH_ERROR'

    name = result.get('name')
    ter = result.get('ter')

    # Check for missing data
    if name is None:
        return 'FETCH_ERROR'

    if ter is None:
        # TER extraction failed, but name might be correct
        return 'TER_MISSING'

    # Compare
    name_ok = names_match(name, ref_name)
    ter_ok = ters_match(ter, ref_ter)

    if name_ok and ter_ok:
        return 'MATCH'
    elif not name_ok and not ter_ok:
        return 'BOTH_MISMATCH'
    elif not name_ok:
        return 'NAME_MISMATCH'
    else:  # not ter_ok
        return 'TER_MISMATCH'


def bootstrap_reference(inputs_dir: str, output_path: str) -> Dict:
    """Auto-generate reference.json if missing."""
    if os.path.exists(output_path):
        logger.info(f"Ground truth loaded from {output_path}")
        with open(output_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        logger.info(f"Generating {output_path} from PDFs...")
        return reference.extract_reference(inputs_dir, output_path)


def bootstrap_sources(isins: List[str], output_path: str) -> Dict:
    """Auto-generate sources.json if missing."""
    if os.path.exists(output_path):
        logger.info(f"Source URLs loaded from {output_path}")
        with open(output_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        logger.info(f"Generating {output_path} from curated list...")
        return curated_sources.generate_sources(isins, output_path)


def load_state(state_path: str) -> Dict:
    """Load mismatch state from file."""
    if not os.path.exists(state_path):
        return {"mismatches": {}}

    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return {"mismatches": {}}


def save_state(state: Dict, state_path: str):
    """Save mismatch state to file."""
    output_dir = os.path.dirname(state_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def generate_report_markdown(results: List[Dict], ref_data: Dict, output_path: str):
    """Generate human-readable markdown report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# ETF Monitoring Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Group by ISIN
        by_isin = {}
        for result in results:
            isin = result['isin']
            if isin not in by_isin:
                by_isin[isin] = []
            by_isin[isin].append(result)

        for isin, isin_results in by_isin.items():
            ref = ref_data[isin]
            f.write(f"## {isin}\n")
            f.write(f"**Reference:** {ref['name']} | TER: {ref['ter']}%\n\n")

            for result in isin_results:
                url = result['url']
                status = result['status']
                name = result.get('name', 'N/A')
                name_source = result.get('name_source', 'unknown')
                ter = result.get('ter', 'N/A')
                ter_evidence = result.get('ter_evidence', '')
                error = result.get('error')

                # Status emoji
                emoji = {
                    'MATCH': '✅',
                    'NAME_MISMATCH': '❌',
                    'TER_MISMATCH': '❌',
                    'BOTH_MISMATCH': '❌',
                    'TER_MISSING': '⚠️',
                    'FETCH_ERROR': '⚠️'
                }.get(status, '❓')

                f.write(f"### {url}\n")
                f.write(f"{emoji} **{status}**\n")

                if error:
                    f.write(f"- Error: {error}\n")
                else:
                    # Name comparison
                    if status in ['NAME_MISMATCH', 'BOTH_MISMATCH']:
                        f.write(f"- Expected: {ref['name']}\n")
                        f.write(f"- Actual: {name} (source: {name_source})\n")
                    else:
                        f.write(f"- Name: {name} (source: {name_source})\n")

                    # TER comparison
                    if status == 'TER_MISSING':
                        f.write(f"- TER: Not found\n")
                    elif status in ['TER_MISMATCH', 'BOTH_MISMATCH']:
                        f.write(f"- Expected TER: {ref['ter']}%\n")
                        f.write(f"- Actual TER: {ter}%\n")
                        if ter_evidence:
                            f.write(f"- Evidence: \"{ter_evidence}\"\n")
                    else:
                        ter_display = f"{ter}%" if isinstance(ter, (int, float)) else ter
                        f.write(f"- TER: {ter_display} ✅\n")
                        if ter_evidence:
                            f.write(f"- Evidence: \"{ter_evidence}\"\n")

                f.write("\n")

    logger.info(f"Report saved to {output_path}")


def generate_report_csv(results: List[Dict], ref_data: Dict, output_path: str):
    """Generate machine-readable CSV report."""
    import csv

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'isin', 'url', 'status', 'expected_name', 'actual_name', 'name_source',
            'expected_ter', 'actual_ter', 'ter_evidence', 'error'
        ])

        for result in results:
            isin = result['isin']
            ref = ref_data[isin]

            writer.writerow([
                isin,
                result['url'],
                result['status'],
                ref['name'],
                result.get('name', ''),
                result.get('name_source', ''),
                ref['ter'],
                result.get('ter', ''),
                result.get('ter_evidence', ''),
                result.get('error', '')
            ])

    logger.info(f"CSV report saved to {output_path}")


def detect_state_changes(
    current_results: List[Dict],
    previous_state: Dict,
    ref_data: Dict
) -> tuple[List[Dict], List[Dict]]:
    """
    Detect new and resolved mismatches by comparing with previous state.
    Returns (new_mismatches, resolved_mismatches)
    """
    new_mismatches = []
    resolved_mismatches = []

    current_mismatches = {}

    # Build current mismatch map
    for result in current_results:
        status = result['status']
        if status in ['NAME_MISMATCH', 'TER_MISMATCH', 'BOTH_MISMATCH']:
            key = f"{result['isin']}|{result['url']}"
            current_mismatches[key] = {
                'isin': result['isin'],
                'url': result['url'],
                'type': 'name' if status == 'NAME_MISMATCH' else ('ter' if status == 'TER_MISMATCH' else 'both'),
                'expected': {
                    'name': ref_data[result['isin']]['name'],
                    'ter': ref_data[result['isin']]['ter']
                },
                'actual': {
                    'name': result.get('name'),
                    'ter': result.get('ter')
                },
                'first_seen': datetime.utcnow().isoformat() + 'Z',
                'last_seen': datetime.utcnow().isoformat() + 'Z'
            }

    # Check for new mismatches
    for key, mismatch in current_mismatches.items():
        if key not in previous_state['mismatches']:
            new_mismatches.append(mismatch)

    # Check for resolved mismatches
    for key, old_mismatch in previous_state['mismatches'].items():
        if key not in current_mismatches:
            resolved_mismatches.append(old_mismatch)

    return new_mismatches, resolved_mismatches


def update_state(
    previous_state: Dict,
    current_results: List[Dict],
    ref_data: Dict
) -> Dict:
    """Update state with current results."""
    new_state = {"mismatches": {}}

    for result in current_results:
        status = result['status']
        if status in ['NAME_MISMATCH', 'TER_MISMATCH', 'BOTH_MISMATCH']:
            key = f"{result['isin']}|{result['url']}"

            if key in previous_state['mismatches']:
                # Update last_seen
                new_state['mismatches'][key] = previous_state['mismatches'][key]
                new_state['mismatches'][key]['last_seen'] = datetime.utcnow().isoformat() + 'Z'
            else:
                # New mismatch
                new_state['mismatches'][key] = {
                    'isin': result['isin'],
                    'url': result['url'],
                    'type': 'name' if status == 'NAME_MISMATCH' else ('ter' if status == 'TER_MISMATCH' else 'both'),
                    'expected': {
                        'name': ref_data[result['isin']]['name'],
                        'ter': ref_data[result['isin']]['ter']
                    },
                    'actual': {
                        'name': result.get('name'),
                        'ter': result.get('ter')
                    },
                    'first_seen': datetime.utcnow().isoformat() + 'Z',
                    'last_seen': datetime.utcnow().isoformat() + 'Z'
                }

    return new_state


def main():
    parser = argparse.ArgumentParser(description="ETF Name + TER Consistency Monitor")

    # Core
    parser.add_argument("--isins", default="LU3098954871,LU3075459852",
                        help="Comma-separated ISINs to monitor")
    parser.add_argument("--inputs-dir", default="inputs",
                        help="Directory containing PDF factsheets")

    # Source discovery
    parser.add_argument("--augment-with-search", action="store_true",
                        help="Add DuckDuckGo search results (default: OFF)")
    parser.add_argument("--search-ttl-days", type=int, default=14,
                        help="TTL for search cache in days")
    parser.add_argument("--max-search-results", type=int, default=5,
                        help="Max additional URLs from search per ISIN")

    # Scraping
    parser.add_argument("--timeout-seconds", type=int, default=10,
                        help="HTTP timeout in seconds")
    parser.add_argument("--sleep-ms", type=int, default=250,
                        help="Sleep between requests in milliseconds")
    parser.add_argument("--max-results", type=int, default=20,
                        help="Max URLs to check per run")

    # Slack
    parser.add_argument("--slack-enabled", action="store_true",
                        help="Enable Slack notifications (auto-detected from env)")
    parser.add_argument("--slack-summary", action="store_true",
                        help="Send one summary per run")

    # LLM
    parser.add_argument("--llm-fallback", action="store_true",
                        help="Enable Claude API for difficult pages (default: OFF)")
    parser.add_argument("--llm-max-calls", type=int, default=3,
                        help="Hard limit for LLM calls per run")

    args = parser.parse_args()

    # Parse ISINs
    isins = [isin.strip() for isin in args.isins.split(',')]
    logger.info(f"Monitoring ISINs: {isins}")

    # Auto-detect Slack
    slack_enabled = args.slack_enabled or os.getenv("SLACK_WEBHOOK_URL") is not None

    # 1. Bootstrap reference
    ref_data = bootstrap_reference(args.inputs_dir, "outputs/reference.json")
    if not ref_data:
        logger.error("Failed to load or generate reference data")
        sys.exit(1)

    # 2. Bootstrap sources
    sources = bootstrap_sources(isins, "outputs/sources.json")

    # 3. Optional search augmentation
    if args.augment_with_search:
        logger.info("Augmenting sources with DuckDuckGo search...")
        etf_names = {isin: ref_data[isin]['name'] for isin in isins}
        sources = search_discovery.augment_sources(
            sources,
            isins,
            etf_names,
            max_results=args.max_search_results,
            ttl_days=args.search_ttl_days
        )

    # 4. Extract from web
    results = []
    llm_call_count = 0

    for isin in isins:
        if isin not in sources:
            logger.warning(f"No sources found for {isin}")
            continue

        urls = sources[isin]['urls'][:args.max_results]
        logger.info(f"Checking {len(urls)} URLs for {isin}...")

        for url in urls:
            logger.info(f"Fetching {url}...")
            result = extract_web.extract_from_url(
                url,
                timeout=args.timeout_seconds,
                sleep_ms=args.sleep_ms
            )
            result['isin'] = isin

            # Optional LLM fallback
            if args.llm_fallback and llm_call_count < args.llm_max_calls:
                if result.get('name') is None or result.get('ter') is None:
                    logger.info(f"Using LLM fallback for {url}")
                    html = extract_web.fetch_url(url, args.timeout_seconds)
                    if html:
                        llm_result = llm_fallback.extract_with_llm(html, url)
                        if llm_result.get('name'):
                            result['name'] = llm_result['name']
                            result['name_source'] = 'llm'
                        if llm_result.get('ter'):
                            result['ter'] = llm_result['ter']
                            result['ter_evidence'] = 'Extracted by LLM'
                        llm_call_count += 1

            # Compare with reference
            ref = ref_data[isin]
            status = compare_result(result, ref['name'], ref['ter'])
            result['status'] = status

            results.append(result)

    logger.info(f"Completed extraction for {len(results)} URLs")
    if args.llm_fallback:
        logger.info(f"LLM calls used: {llm_call_count}/{args.llm_max_calls}")

    # 5. Generate reports
    generate_report_markdown(results, ref_data, "outputs/report.md")
    generate_report_csv(results, ref_data, "outputs/report.csv")

    # 6. State management and Slack notifications
    previous_state = load_state("outputs/state.json")
    new_mismatches, resolved_mismatches = detect_state_changes(results, previous_state, ref_data)

    if slack_enabled:
        logger.info("Checking for Slack notifications...")

        # Send alerts for new mismatches
        for mismatch in new_mismatches:
            logger.info(f"New mismatch: {mismatch['isin']} - {mismatch['url']}")
            notify_slack.notify_new_mismatch(mismatch)

        # Send alerts for resolved mismatches
        for mismatch in resolved_mismatches:
            logger.info(f"Resolved mismatch: {mismatch['isin']} - {mismatch['url']}")
            notify_slack.notify_resolved_mismatch(mismatch)

        # Optional summary
        if args.slack_summary:
            notify_slack.notify_summary(results, ref_data)

    # Update state
    new_state = update_state(previous_state, results, ref_data)
    save_state(new_state, "outputs/state.json")

    # Summary
    logger.info("=== Summary ===")
    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        logger.info(f"{status}: {count}")

    logger.info(f"New mismatches: {len(new_mismatches)}")
    logger.info(f"Resolved mismatches: {len(resolved_mismatches)}")


if __name__ == "__main__":
    main()
