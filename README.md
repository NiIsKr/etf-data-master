# ETF Data Monitor

Web-based monitoring dashboard for tracking ETF data consistency across financial websites.

## What It Does

- Monitors ETF names and TER (Total Expense Ratio) across major German financial sites
- Per-ETF architecture for fast, reliable checks
- AI-powered extraction using Claude Haiku
- Clean, Apple-like UI

## Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd etf-monitor
```

### 2. Configure Environment

Create `.env` file:
```
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Deploy to Vercel

```bash
vercel
```

That's it! Open your Vercel URL.

## How It Works

1. Click "Check TEQ" or "Check Inyova"
2. System fetches HTML from 8 financial websites per ETF
3. Claude Haiku extracts name + TER from each site
4. Results compared against reference data
5. Dashboard shows matches/mismatches with detailed explanations

## Architecture

### Frontend (`/public`)
- `index.html` - Main dashboard
- `css/style.css` - Apple-like design system
- `js/app.js` - Per-ETF monitoring logic

### Backend (`/api`)
- `monitor.py` - Serverless function (Vercel)
- `config.py` - Centralized ETF/datapoint configuration

### Tech Stack
- **Frontend:** Vanilla JS, CSS (no frameworks)
- **Backend:** Python 3.9, Anthropic API
- **Hosting:** Vercel (serverless)
- **AI:** Claude Haiku for intelligent extraction

## Adding New ETFs

Edit `/api/config.py`:

```python
ETFS = {
    "LU1234567890": {
        "name": "New ETF Name",
        "short_name": "NEW",
        "datapoints": {
            "ter": 0.50
        }
    },
    # ... existing ETFs
}

SOURCES_OVERRIDE = {
    "LU1234567890": [
        "https://www.onvista.de/etf/...",
        "https://de.finance.yahoo.com/quote/..."
    ]
}
```

Deploy and done! No code changes needed.

## Adding New Datapoints (Future)

To add AUM tracking:

1. Update `config.py`:
```python
DATAPOINT_CONFIG = {
    "aum": {
        "label": "Assets Under Management",
        "unit": "M€",
        "keywords": ['AUM', 'Fondsvermögen'],
        "regex": r'(\d+[.,]?\d*)\s*(?:M€|Mio)',
        "required": False
    }
}
```

2. Add to ETF configs:
```python
"datapoints": {
    "ter": 0.69,
    "aum": 250.5
}
```

3. Update extraction logic in `monitor.py` to handle new datapoint.

## Performance

- **Per-ETF Check:** ~25-30 seconds
- **Token Usage:** ~22,000-28,000 per check
- **Rate Limit:** 45% safety margin below Anthropic limits
- **Consistency:** 100% (zero variance)

## Project Structure

```
etf-monitor/
├── public/              # Frontend (HTML, CSS, JS)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── api/                 # Vercel serverless functions
│   ├── monitor.py       # Main API endpoint
│   └── config.py        # ETF/datapoint configuration
├── .env                 # Environment variables
├── vercel.json          # Vercel config
└── README.md            # This file
```

## Development

### Local Testing
(Note: Requires Anthropic API key configured)

```bash
# Install dependencies
pip3 install requests anthropic beautifulsoup4

# Run local test server
python3 test_server_v2.py

# Open http://localhost:3000
```

### Deployment

```bash
git add .
git commit -m "Your changes"
git push

# Vercel auto-deploys from main branch
```

## Troubleshooting

**429 Rate Limit Errors?**
- Use per-ETF buttons (not "Check ALL" if it exists)
- Each ETF check is well below rate limits

**TER Not Found?**
- Check browser console for details
- Some sites may have changed HTML structure
- Yahoo Finance requires deeper HTML parsing

**Slow Performance?**
- Normal: Each check makes 8 API calls to Claude
- Per-ETF checks are ~40% faster than checking all

## Cost

- **Anthropic API:** ~$0.001-0.002 per check
- **Hosting:** Free (Vercel hobby tier)
- **Monthly:** ~$3-5 for regular monitoring

## License

Private project.
