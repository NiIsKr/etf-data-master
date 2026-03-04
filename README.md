# ETF Name + TER Consistency Monitor

Ultra-minimal, terminal-first monitoring system that tracks ETF name and TER consistency across web sources.

## What it does

- Extracts ground truth from official ETF factsheets (PDFs)
- Scrapes ETF name and TER from top financial websites
- Compares web data against ground truth using strict matching
- Alerts via Slack ONLY on status changes (new mismatch or resolved)
- Runs with near-zero API costs in production

## Quickstart

### 1. One-time setup (2 minutes)

```bash
cd ~/Desktop/DEV/etf-monitor
chmod +x setup.sh run.sh
./setup.sh
```

This will:
- Create a Python virtual environment
- Install dependencies
- Create outputs directory
- Set up `.env` file

### 2. Add PDFs

Copy or symlink your ETF factsheet PDFs to the `inputs/` directory:

```bash
# If you already have the PDFs in another directory
cp ~/path/to/FS_LU3098954871_de.pdf inputs/
cp ~/path/to/fwwdok_dxjMduzPQS.pdf inputs/
```

### 3. Optional: Configure Slack

Edit `.env` and add your Slack webhook URL:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Get your webhook URL from: https://api.slack.com/messaging/webhooks

### 4. First run

```bash
./run.sh
```

Check the results:
```bash
cat outputs/report.md     # Human-readable report
cat outputs/report.csv    # Machine-readable report
```

### 5. Schedule daily runs

```bash
crontab -e
```

Add this line (runs daily at 8 AM):
```cron
0 8 * * * cd ~/Desktop/DEV/etf-monitor && ./run.sh >> logs/daily.log 2>&1
```

## Optional Flags

```bash
./run.sh --augment-with-search     # Add DuckDuckGo search results
./run.sh --llm-fallback            # Enable LLM for difficult pages
./run.sh --slack-summary           # Send one summary per run
```

## What Gets Checked

**Two ETFs:**
- TEQ (ISIN: LU3098954871) - General AI ETF
- Inyova (ISIN: LU3075459852) - Impact Investing ETF

**Sources checked per ETF (~9 URLs):**
- JustETF
- ExtraETF
- Finanzfluss
- Comdirect
- AVL Investmentfonds
- Finanzen.net
- OnVista
- Yahoo Finance
- Deutsche Börse

## Reports

### outputs/report.md
Human-readable report with:
- Status for each URL (✅ MATCH, ❌ MISMATCH, ⚠️ WARNINGS)
- Name extraction source (og:title, h1, title, etc.)
- TER extraction evidence (text snippet showing where TER was found)

### outputs/report.csv
Machine-readable CSV with all details for further analysis.

### outputs/state.json
Tracks mismatches over time to enable smart Slack alerts (only on changes).

## Comparison Rules

**Strict mode:**
- **Name:** Any deviation = mismatch (only whitespace normalization)
- **TER:** Exact numeric match after rounding to 4 decimals (0.9500 == 0.95 ok)

## Slack Notifications

**You will receive alerts for:**
- 🚨 New mismatch detected
- ✅ Mismatch resolved

**You will NOT receive alerts for:**
- Existing mismatches (already reported)
- TER extraction failures (logged in reports only)
- Fetch errors (timeouts, HTTP errors)

## Cost

**Default operation: $0/month**
- No search API calls (uses curated URL list)
- No LLM calls (heuristics only)
- No hosting/database costs

**With optional flags:**
- `--augment-with-search`: Free (DuckDuckGo HTML)
- `--llm-fallback`: ~$0.0002 per URL (max 3 calls/run = ~$0.0006/run)

## Files

```
etf-monitor/
├── inputs/              # Your PDF factsheets
├── outputs/            # Generated reports (gitignored)
├── logs/               # Cron logs
├── src/                # Python source code
├── tests/              # Unit tests
├── setup.sh            # One-time setup
├── run.sh              # Daily runner
└── .env                # Config (Slack webhook, etc.)
```

## Testing

Run unit tests:
```bash
source venv/bin/activate
python -m pytest tests/ -v
```

Or run tests directly:
```bash
python tests/test_compare.py
python tests/test_extract_web.py
```

## Troubleshooting

**"inputs/ folder not found"**
- Create it: `mkdir inputs`

**"PDF not found"**
- Check that PDFs are in `inputs/` directory
- Required filenames:
  - `FS_LU3098954871_de.pdf` (TEQ)
  - `fwwdok_dxjMduzPQS.pdf` (Inyova)

**"SLACK_WEBHOOK_URL not set"**
- This is just a warning - Slack is optional
- To enable: edit `.env` and add your webhook URL

**TER extraction failing for many sites**
- Check `outputs/report.md` for evidence fields
- Consider using `--llm-fallback` flag (costs ~$0.0006/run)

## Manual Commands

You can also run individual components:

```bash
source venv/bin/activate

# Extract reference from PDFs
python -m src.reference

# Generate source URLs
python -m src.curated_sources

# Test web extraction on a single URL
python -m src.extract_web "https://www.justetf.com/de/etf-profile.html?isin=LU3098954871"

# Run monitor with custom options
python -m src.monitor --isins LU3098954871,LU3075459852 --augment-with-search
```

## How It Works

1. **Extract ground truth** from PDF factsheets (name + TER)
2. **Generate URL list** from curated templates + hardcoded overrides
3. **Fetch and parse** HTML from each URL
4. **Compare** extracted data with ground truth (strict matching)
5. **Generate reports** (markdown + CSV)
6. **Send Slack alerts** only on NEW or RESOLVED mismatches
7. **Update state** for next run

## Non-Negotiables

- ✅ No paid services (no cloud, no databases, no Docker)
- ✅ Public web only (HTTP GET to public sites)
- ✅ Curated sources (manually maintained list)
- ✅ Minimal LLM usage (default: 0 calls, optional flag with hard limit)
- ✅ Strict comparison (any deviation = mismatch)

## Support

For issues or questions, check:
- `outputs/report.md` for detailed extraction results
- `logs/daily.log` for cron output
- `outputs/state.json` for mismatch history

## License

Private project - all rights reserved.
