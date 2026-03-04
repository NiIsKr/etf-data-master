"""
Slack webhook notifications.
"""
import os
import logging
import json
from typing import Dict, List
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


def send_slack_message(message: str, webhook_url: str = None) -> bool:
    """
    Send a message to Slack via webhook.
    Returns True on success, False on failure.
    """
    if webhook_url is None:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        logger.error("SLACK_WEBHOOK_URL not configured")
        return False

    payload = {"text": message}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Slack notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return False


def format_mismatch_message(mismatch: Dict) -> str:
    """
    Format a mismatch notification for Slack.

    Args:
        mismatch: Dict with keys: isin, url, type, expected, actual
    """
    isin = mismatch['isin']
    url = mismatch['url']
    mismatch_type = mismatch['type']
    expected = mismatch['expected']
    actual = mismatch['actual']

    message = f"🚨 *ETF Mismatch Detected*\n\n"
    message += f"*ETF:* {isin}\n"
    message += f"*Source:* {url}\n\n"

    if mismatch_type in ['name', 'both']:
        message += f"❌ *Name mismatch*\n"
        message += f"Expected: \"{expected['name']}\"\n"
        message += f"Actual: \"{actual['name']}\"\n\n"

    if mismatch_type in ['ter', 'both']:
        message += f"❌ *TER mismatch*\n"
        message += f"Expected: {expected['ter']}%\n"
        message += f"Actual: {actual['ter']}%\n"

    return message


def format_resolved_message(mismatch: Dict) -> str:
    """Format a resolved mismatch notification for Slack."""
    isin = mismatch['isin']
    url = mismatch['url']
    mismatch_type = mismatch['type']

    message = f"✅ *ETF Mismatch Resolved*\n\n"
    message += f"*ETF:* {isin}\n"
    message += f"*Source:* {url}\n\n"

    if mismatch_type in ['name', 'both']:
        message += "✓ Name now matches\n"

    if mismatch_type in ['ter', 'both']:
        message += "✓ TER now matches\n"

    return message


def format_summary_message(results: List[Dict], reference: Dict) -> str:
    """
    Format a summary message for Slack.

    Args:
        results: List of extraction results with status
        reference: Reference data dict
    """
    # Count statuses
    status_counts = {}
    for result in results:
        status = result.get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1

    # Count mismatches
    total_mismatches = sum(
        count for status, count in status_counts.items()
        if status in ['NAME_MISMATCH', 'TER_MISMATCH', 'BOTH_MISMATCH']
    )

    message = f"📊 *ETF Monitor Summary*\n\n"
    message += f"*Total sources checked:* {len(results)}\n"
    message += f"*Mismatches found:* {total_mismatches}\n\n"

    message += "*Status breakdown:*\n"
    for status, count in sorted(status_counts.items()):
        emoji = {
            'MATCH': '✅',
            'NAME_MISMATCH': '❌',
            'TER_MISMATCH': '❌',
            'BOTH_MISMATCH': '❌',
            'TER_MISSING': '⚠️',
            'FETCH_ERROR': '⚠️'
        }.get(status, '❓')
        message += f"{emoji} {status}: {count}\n"

    return message


def notify_new_mismatch(mismatch: Dict, webhook_url: str = None) -> bool:
    """Send notification for a new mismatch."""
    message = format_mismatch_message(mismatch)
    return send_slack_message(message, webhook_url)


def notify_resolved_mismatch(mismatch: Dict, webhook_url: str = None) -> bool:
    """Send notification for a resolved mismatch."""
    message = format_resolved_message(mismatch)
    return send_slack_message(message, webhook_url)


def notify_summary(results: List[Dict], reference: Dict, webhook_url: str = None) -> bool:
    """Send summary notification."""
    message = format_summary_message(results, reference)
    return send_slack_message(message, webhook_url)


if __name__ == "__main__":
    # Test notification
    test_mismatch = {
        "isin": "LU3098954871",
        "url": "https://example.com",
        "type": "both",
        "expected": {"name": "Test ETF Name", "ter": 0.69},
        "actual": {"name": "Wrong Name", "ter": 0.70}
    }

    message = format_mismatch_message(test_mismatch)
    print(message)
