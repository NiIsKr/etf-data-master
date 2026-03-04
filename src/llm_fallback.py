"""
Optional LLM fallback for difficult pages using Claude API.
"""
import os
import logging
import json
from typing import Optional, Dict
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


def extract_with_llm(html: str, url: str) -> Dict:
    """
    Extract ETF name and TER using Claude API.
    Returns dict: {name: str|None, ter: float|None, error: str|None}
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.error("anthropic package not installed. Install with: pip install -r requirements-llm.txt")
        return {"name": None, "ter": None, "error": "anthropic package not installed"}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return {"name": None, "ter": None, "error": "ANTHROPIC_API_KEY not set"}

    # Truncate HTML if too long (focus on body content)
    if len(html) > 20000:
        # Try to extract body content
        import re
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
        if body_match:
            html = body_match.group(1)
        # Still truncate if needed
        html = html[:20000]

    prompt = f"""Extract the ETF name and TER (Total Expense Ratio / laufende Kosten) from this HTML.

URL: {url}

Return a JSON object with this exact structure:
{{
  "name": "the full ETF name",
  "ter": 0.69
}}

If you cannot find the name, set "name" to null.
If you cannot find the TER, set "ter" to null.
TER should be a number representing the percentage (e.g., 0.69 for 0.69%).

HTML:
{html}
"""

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        content = response.content[0].text
        # Extract JSON from response (may be wrapped in markdown code block)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            logger.info(f"LLM extracted: name={data.get('name')}, ter={data.get('ter')}")
            return {
                "name": data.get("name"),
                "ter": data.get("ter"),
                "error": None
            }
        else:
            logger.error("Could not parse JSON from LLM response")
            return {"name": None, "ter": None, "error": "Failed to parse LLM response"}

    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return {"name": None, "ter": None, "error": str(e)}


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.llm_fallback <url>")
        sys.exit(1)

    url = sys.argv[1]

    # Fetch HTML
    import requests
    response = requests.get(url, timeout=10)
    html = response.text

    result = extract_with_llm(html, url)
    print(json.dumps(result, indent=2))
