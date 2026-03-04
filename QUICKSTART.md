# ETF Monitor - Quick Start Guide

## For First-Time Users

### Step 1: Setup (one-time, 2 minutes)

```bash
cd ~/Desktop/DEV/etf-monitor
./setup.sh
```

This will:
- Create Python virtual environment
- Install dependencies
- Create output directories
- Set up `.env` file

### Step 2: Run the monitor

```bash
./run.sh
```

This will:
- Auto-extract ground truth from PDFs (first run only)
- Auto-generate source URLs (first run only)
- Check 18 URLs (9 per ETF)
- Generate reports in `outputs/`

### Step 3: Check the results

```bash
cat outputs/report.md     # Human-readable report
cat outputs/report.csv    # Machine-readable CSV
```

### Step 4: Schedule daily runs (optional)

```bash
crontab -e
```

Add this line:
```cron
0 8 * * * cd ~/Desktop/DEV/etf-monitor && ./run.sh >> logs/daily.log 2>&1
```

## Optional: Enable Slack Notifications

1. Get a Slack webhook URL: https://api.slack.com/messaging/webhooks

2. Edit `.env`:
   ```bash
   nano .env
   ```

3. Add your webhook:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

4. Run again:
   ```bash
   ./run.sh
   ```

You'll receive Slack alerts for:
- 🚨 New mismatches detected
- ✅ Mismatches resolved

## Optional Flags

```bash
# Add DuckDuckGo search results (cached for 14 days)
./run.sh --augment-with-search

# Enable LLM fallback for difficult pages (costs ~$0.0006/run)
./run.sh --llm-fallback

# Send summary message after each run
./run.sh --slack-summary
```

## What Gets Checked

**ETFs:**
- TEQ (ISIN: LU3098954871) - TER: 0.69%
- Inyova (ISIN: LU3075459852) - TER: 0.95%

**Sources (9 per ETF):**
- JustETF
- ExtraETF
- Finanzfluss
- Comdirect
- AVL Investmentfonds
- Finanzen.net
- OnVista
- Yahoo Finance
- Deutsche Börse

**What we check:**
- ETF name (strict: any deviation = mismatch)
- TER (strict: rounded to 4 decimals)

## Files Generated

```
outputs/
├── reference.json    # Ground truth from PDFs
├── sources.json      # URLs to check
├── report.md         # Human-readable report
├── report.csv        # Machine-readable CSV
└── state.json        # Mismatch tracking for Slack alerts
```

## Troubleshooting

**Problem:** `inputs/ folder not found`
**Solution:** `mkdir inputs` and copy your PDF files there

**Problem:** `PDF not found`
**Solution:** Make sure PDFs are named correctly:
- `FS_LU3098954871_de.pdf` (TEQ)
- `fwwdok_dxjMduzPQS.pdf` (Inyova)

**Problem:** TER extraction failing
**Solution:** Check `outputs/report.md` for evidence fields, or try `./run.sh --llm-fallback`

**Problem:** Slack not working
**Solution:** Make sure `SLACK_WEBHOOK_URL` is set in `.env`

## Testing

Run unit tests:
```bash
source venv/bin/activate
python tests/test_compare.py
python tests/test_extract_web.py
```

## Cost

**Default operation:** $0/month
- Curated sources only (no search calls)
- Heuristic extraction only (no LLM calls)

**With --llm-fallback:** ~$0.0006/run (~$0.02/month for daily runs)

## Need Help?

- Check `README.md` for detailed documentation
- Check `CLAUDE.md` for technical details
- Check `outputs/report.md` for extraction evidence
- Check `logs/daily.log` for cron output

## Example Output

```markdown
## LU3098954871
**Reference:** TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc) | TER: 0.69%

### https://www.justetf.com/de/etf-profile.html?isin=LU3098954871
✅ **MATCH**
- Name: TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc) (source: og:title)
- TER: 0.69% ✅ (evidence: "...Gesamtkostenquote (TER): 0,69 % p.a....")

### https://www.finanzen.net/etf/teq-general-artificial-intelligence-etf-r-lu3098954871
❌ **NAME_MISMATCH**
- Expected: TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc)
- Actual: TEQ General Artificial Intelligence ETF (source: h1)
- TER: 0.69% ✅ (evidence: "...laufende Kosten von 0,69%...")
```

That's it! You're monitoring ETF consistency across the web. 🎉
