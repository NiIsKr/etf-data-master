# ETF Name + TER Consistency Monitor - Project Documentation

## Project Goal

Monitor ETF name and TER (Total Expense Ratio) consistency across financial websites to detect discrepancies with official factsheet data. Alert only on status changes (new mismatches or resolutions) via Slack.

## Why This Exists

After ETF go-live, ETF names and TER are displayed inconsistently across broker platforms, comparison websites, and search results. This leads to confusion and potential misrepresentation. This tool automatically monitors these inconsistencies.

## Scope

**ETFs monitored:**
- TEQ (ISIN: LU3098954871) - General Artificial Intelligence R EUR UCITS ETF (Acc)
- Inyova (ISIN: LU3075459852) - Impact Investing Active Equity Fund UCITS ETF EUR

**What we check:**
- ETF name (strict: any deviation = mismatch)
- TER / laufende Kosten (strict: rounded to 4 decimals)

**What we DON'T check:**
- ISIN accuracy
- Launch date
- Fund size / AUM
- Performance data
- Other fund characteristics

## Non-Negotiables

1. **No paid services**: No paid APIs, no cloud services, no databases, no Docker, no hosting
2. **Public web only**: HTTP GET/HEAD to public websites only
3. **Curated sources**: Manually maintained list of known ETF info sites (no search engine scraping by default)
4. **Respect limits**: Rate limiting, timeouts, no login/paywall/CAPTCHA circumvention
5. **Minimal LLM usage**: Default 0 LLM calls per run; optional `--llm-fallback` flag with max 3 calls/run hard limit
6. **Strict comparison mode**:
   - **Name**: Any deviation = mismatch (only whitespace normalization: strip + collapse spaces)
   - **TER**: Exact numeric match after rounding to 4 decimals (0.9500 == 0.95 ok)

## Architecture

### Components

1. **reference.py** - Extract ground truth from PDF factsheets
2. **curated_sources.py** - Generate URL list from templates + overrides
3. **source_overrides.json** - Hardcoded URLs for sites without ISIN patterns
4. **search_discovery.py** - Optional DuckDuckGo HTML augmentation
5. **extract_web.py** - Fetch HTML and extract name + TER using heuristics
6. **llm_fallback.py** - Optional Claude API extraction for difficult pages
7. **notify_slack.py** - Slack webhook notifications
8. **monitor.py** - Main orchestration with auto-bootstrap

### Data Flow

```
1. PDFs → reference.py → outputs/reference.json (ground truth)
2. ISINs → curated_sources.py → outputs/sources.json (URLs to check)
3. Optional: --augment-with-search → search_discovery.py → more URLs
4. URLs → extract_web.py → name + TER extraction
5. Optional: --llm-fallback → llm_fallback.py → retry failed extractions
6. Compare → monitor.py → outputs/report.md + report.csv
7. State change detection → notify_slack.py → Slack alerts
8. Update outputs/state.json for next run
```

### Auto-Bootstrap

`monitor.py` automatically generates missing files:
- If `outputs/reference.json` missing → calls `reference.extract_reference()`
- If `outputs/sources.json` missing → calls `curated_sources.generate_sources()`

User never needs to run these modules separately!

## Curated Sources

**ISIN-based templates (5 sites):**
- JustETF: `https://www.justetf.com/de/etf-profile.html?isin={ISIN}`
- ExtraETF: `https://extraetf.com/de/etf-profile/{ISIN}`
- Finanzfluss: `https://www.finanzfluss.de/informer/etf/{isin_lower}/`
- Comdirect: `https://www.comdirect.de/inf/etfs/{ISIN}`
- AVL: `https://www.avl-investmentfonds.de/fonds/details/{ISIN}`

**Hardcoded overrides (4 sites per ETF):**
- Finanzen.net (uses slugs, not ISIN)
- OnVista (uses slugs, not ISIN)
- Yahoo Finance (uses ticker symbols)
- Deutsche Börse (uses slugs, not ISIN)

**Total: 9 URLs per ETF = 18 URLs checked per run**

## Extraction Strategy

### Name Extraction (Priority Order)

1. `<meta property="og:title">` - Most reliable
2. JSON-LD structured data (`@type: "FinancialProduct"`)
3. `<h1>` tag
4. `<title>` tag (cleaned)
5. Fallback: "Unknown"

### TER Extraction

**Keywords searched:**
- TER
- Total Expense Ratio
- Gesamtkostenquote
- laufende Kosten
- Kostenquote
- Ongoing Charges
- Verwaltungsgebühr

**Regex:** `(\d+[.,]\d{1,4})\s*(?:%|bps)?`

**Context:** 50 chars before, 100 chars after keyword

**Evidence:** 80-120 char snippet saved for debugging

## Comparison Logic

### Name Comparison

```python
def normalize_name(name: str) -> str:
    return ' '.join(name.strip().split())

def names_match(name1: str, name2: str) -> bool:
    return normalize_name(name1) == normalize_name(name2)
```

**What this means:**
- "TEQ ETF" == "TEQ  ETF" (whitespace normalized) ✅
- "TEQ - ETF" != "TEQ ETF" (dash matters) ❌
- "TEQ ETF" != "teq etf" (case matters) ❌

### TER Comparison

```python
def ters_match(ter1: float, ter2: float) -> bool:
    return round(ter1, 4) == round(ter2, 4)
```

**What this means:**
- 0.69 == 0.6900 ✅
- 0.694999 == 0.6950 ✅
- 0.6949 != 0.6950 ❌

## Status Values

- `MATCH` - Name AND TER both match ✅
- `NAME_MISMATCH` - Name differs ❌
- `TER_MISMATCH` - TER differs ❌
- `BOTH_MISMATCH` - Both differ ❌
- `TER_MISSING` - TER not extractable ⚠️
- `FETCH_ERROR` - HTTP error, timeout, or parsing failure ⚠️

**Slack alerts:** Only for NAME_MISMATCH, TER_MISMATCH, BOTH_MISMATCH
**Reports only:** TER_MISSING, FETCH_ERROR (no alerts)

## State Management

**File:** `outputs/state.json`

**Purpose:** Track mismatches over time to enable smart Slack alerts

**Structure:**
```json
{
  "mismatches": {
    "ISIN|URL": {
      "isin": "...",
      "url": "...",
      "type": "name|ter|both",
      "expected": {"name": "...", "ter": 0.69},
      "actual": {"name": "...", "ter": 0.70},
      "first_seen": "2026-03-01T12:00:00Z",
      "last_seen": "2026-03-01T12:00:00Z"
    }
  }
}
```

**Logic:**
- New mismatch not in state → Send Slack alert + add to state
- Existing mismatch still present → Update `last_seen`, no alert
- Old mismatch now resolved → Send Slack alert + remove from state

## User Interface

**For non-programmers:**

```bash
# One-time setup
./setup.sh

# Daily run (via cron or manual)
./run.sh
```

**That's it!** No Python knowledge required.

**Optional flags:**
```bash
./run.sh --augment-with-search  # Add search results
./run.sh --llm-fallback         # Enable LLM
./run.sh --slack-summary        # Send summary
```

## Cost Analysis

### Default Operation ($0/month)
- Curated sources only (no search API calls)
- Heuristic extraction only (no LLM calls)
- HTTP GET requests to public sites (free)
- Slack webhooks (free)

### With --augment-with-search ($0/month)
- DuckDuckGo HTML scraping (free, no API key needed)
- Cached with 14-day TTL

### With --llm-fallback (~$0.0006/run)
- Claude Haiku model: ~$0.25 per 1M tokens
- Average: ~800 tokens per extraction
- Max 3 calls per run = ~2400 tokens = ~$0.0006/run
- Daily runs = ~$0.02/month

## Development Workflow

### Adding a New Source

1. Check if ISIN-based URL works:
   ```bash
   curl -I "https://newsite.com/etf/{ISIN}"
   ```

2a. If yes → Add template to `src/curated_sources.py`:
   ```python
   ISIN_TEMPLATES = [
       # ... existing ...
       "https://newsite.com/etf/{ISIN}"
   ]
   ```

2b. If no (uses slugs) → Add to `src/source_overrides.json`:
   ```json
   {
     "LU3098954871": [
       "https://newsite.com/etf/teq-slug"
     ]
   }
   ```

3. Delete `outputs/sources.json` to regenerate

4. Test:
   ```bash
   ./run.sh
   cat outputs/report.md | grep newsite
   ```

### Debugging Extraction Issues

1. Check report for evidence fields:
   ```bash
   cat outputs/report.md
   ```

2. Test extraction on single URL:
   ```bash
   source venv/bin/activate
   python -m src.extract_web "https://example.com/etf"
   ```

3. Try LLM fallback:
   ```bash
   ./run.sh --llm-fallback
   ```

4. If still failing → Add custom parser in `extract_web.py`

### Testing Changes

```bash
# Run unit tests
python -m pytest tests/ -v

# Or run directly
python tests/test_compare.py
python tests/test_extract_web.py

# Full integration test
./run.sh
cat outputs/report.md
```

## Known Limitations

1. **JavaScript-only sites** - Cannot parse sites that require JS execution
2. **Login/paywall sites** - Cannot access authenticated content
3. **Dynamic URL structures** - Sites that change URL patterns need manual updates
4. **False positives** - Strict mode intentionally flags minor deviations (by design)
5. **HTML structure changes** - Sites can change HTML at any time, breaking extraction

## Mitigation Strategies

1. **Multi-strategy extraction** - Try multiple methods (og:title, h1, title, json-ld)
2. **Optional LLM fallback** - User can enable for difficult pages
3. **Curated sources** - Focus on stable, server-rendered sites
4. **Evidence fields** - Report includes extraction evidence for debugging
5. **Manual overrides** - TEQ TER hardcoded to 0.69% as fallback

## Future Improvements (If Needed)

- Add more curated sources (other ETF info sites)
- Improve TER regex for edge cases (ranges, multiple TER values)
- Add support for other languages (English factsheets)
- Create dashboard for viewing historical mismatches
- Add email notifications as alternative to Slack

## Maintenance

**Quarterly review (recommended):**
1. Check if any URLs return 404 → Remove from overrides
2. Check if any sites changed HTML structure → Update extraction
3. Review false positives → Consider relaxing strict mode (if needed)
4. Update curated sources list → Add new popular ETF sites

**No ongoing maintenance required** - System runs autonomously once set up.

## Success Criteria

✅ System detects mismatches within 24 hours of appearing on web
✅ False positive rate < 10% (strict mode is intentional)
✅ Slack alerts only on NEW or RESOLVED mismatches (no spam)
✅ Zero cost in default operation
✅ Non-programmer can set up and run with 2 commands
✅ Reports include enough evidence to verify extraction accuracy

## Contact

For questions about this codebase, refer to this document and the implementation plan in the project root.
