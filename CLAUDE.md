# ETF Data Monitor - Developer Guide

## Current Architecture (March 2026)

### Overview
Web-first monitoring dashboard with per-ETF architecture for reliable, fast ETF data validation.

### Key Design Decisions

1. **Per-ETF Architecture**
   - Separate buttons for each ETF
   - Prevents rate limit issues (45% safety margin)
   - 100% consistent results
   - Scales to 10+ ETFs easily

2. **Centralized Configuration**
   - `api/config.py` is single source of truth
   - Adding ETFs = config change only
   - Extensible for new datapoints (AUM, inception date, etc.)

3. **No Unnecessary Features**
   - No Slack webhooks (removed for simplicity)
   - No "Check ALL" button (removed as error-prone)
   - No dynamic subtitle (removed to avoid outdated text)
   - Clean, minimal UI

4. **Apple-like Design**
   - SF Pro font system
   - iOS color palette
   - Subtle animations and depth
   - Glass-morphism effects

### Technology Choices

**Frontend:**
- Vanilla JS (no framework overhead)
- CSS custom properties (theming)
- Semantic HTML

**Backend:**
- Python 3.9 (Vercel runtime)
- Claude Haiku (cost-effective, fast)
- Serverless (zero ops)

**Hosting:**
- Vercel (free tier sufficient)
- Auto-deploys from GitHub

### Data Flow

```
User clicks "Check TEQ"
    ↓
POST /api/monitor { isin: "LU3098954871" }
    ↓
monitor.py loads config for LU3098954871
    ↓
Fetches 8 URLs in parallel (ThreadPoolExecutor)
    ↓
Each URL → Claude Haiku extraction (name + TER)
    ↓
Compare extracted data vs reference
    ↓
Return results with status (MATCH/MISMATCH/MISSING)
    ↓
Frontend displays grouped results with visual indicators
```

### Configuration System

**Single File:** `/api/config.py`

```
ETFS = { ... }                 # ETF definitions
DATAPOINT_CONFIG = { ... }     # What to extract
ISIN_TEMPLATES = [ ... ]       # URL patterns
SOURCES_OVERRIDE = { ... }     # ETF-specific URLs
```

**Adding New ETF:** Edit config.py only, no code changes needed
**Adding New Datapoint:** Update DATAPOINT_CONFIG + extraction logic

### Extraction Strategy

**Name:**
1. Try og:title meta tag
2. Try h1 tag
3. Try title tag
4. Fallback: "Unknown"

**TER:**
1. Search for keywords (TER, Total Expense Ratio, etc.)
2. Extract percentage near keyword
3. Convert bps to % if needed
4. Validate against reference (rounded to 4 decimals)

**Future (AUM, etc.):**
- Same pattern: keywords → regex → validation

### Frontend State Management

**Minimal, localStorage-free:**
- No settings persistence (removed Slack)
- Transient state only (monitoring progress)
- Results fetched fresh each check

**Visual State:**
- Status indicators (green/red dots)
- Last checked timestamps
- Progress bar during checks

### Performance Characteristics

**Token Usage:**
- Per-ETF: 22,000-28,000 tokens (~25-30s)
- Rate limit: 50,000 tokens/min
- Safety margin: 45%

**Scalability:**
- 10 ETFs × 8 URLs = 80 URLs
- Still 22k tokens per ETF check
- Scales linearly with parallel architecture

### Common Modifications

**Add New ETF:**
```python
# config.py
ETFS["LU9999999999"] = {
    "name": "New ETF Name",
    "short_name": "NEW",
    "datapoints": {"ter": 0.45}
}
```

**Add New Source:**
```python
# config.py
SOURCES_OVERRIDE["LU3098954871"].append(
    "https://newsite.com/etf/..."
)
```

**Change UI Colors:**
```css
/* style.css */
:root {
    --primary: #007AFF;  /* Change this */
    --success: #34C759;  /* And this */
}
```

### Testing Strategy

**Manual Testing:**
1. Click each ETF button
2. Verify 8 results appear
3. Check status indicators update
4. Verify no 429 errors

**Adding New Sources:**
1. Add to config
2. Test with single ETF check
3. Verify extraction works
4. Deploy

### Deployment Workflow

```bash
# Local changes
git add .
git commit -m "Description"
git push

# Vercel auto-deploys
# Check deployment at vercel.com/dashboard
# Test live URL
```

### Troubleshooting

**Rate Limits:**
- Check per-ETF (not all)
- Verify token count in logs

**Extraction Failures:**
- Check HTML structure hasn't changed
- Verify keywords in DATAPOINT_CONFIG
- May need to update regex

**UI Issues:**
- Check browser console
- Verify API response format
- Check CSS specificity

### Future Roadmap

1. **More Datapoints:**
   - AUM (Assets Under Management)
   - Inception Date
   - Fund Size

2. **More ETFs:**
   - Easy with config-based system
   - Just add to config.py

3. **Historical Tracking:**
   - Store results over time
   - Show trends

4. **Scheduled Checks:**
   - Vercel Cron Jobs
   - Auto-check daily

### Non-Goals

- ❌ User authentication (single-user tool)
- ❌ Database (stateless, on-demand)
- ❌ Slack integration (removed for simplicity)
- ❌ Check ALL button (error-prone, removed)
- ❌ PDF extraction (web sources only)

### File Ownership

**You should edit:**
- `api/config.py` - ETF/datapoint configuration
- `public/css/style.css` - UI styling
- `README.md` - User documentation

**You probably shouldn't edit:**
- `api/monitor.py` - Core logic (stable)
- `public/js/app.js` - Frontend logic (stable)
- `public/index.html` - Structure (stable)

### Questions for New Developers

1. **How do I add a new ETF?**
   → Edit `api/config.py`, add to ETFS dict

2. **How do I change button colors?**
   → Edit CSS variables in `public/css/style.css`

3. **Where are results stored?**
   → Nowhere! Stateless, on-demand only

4. **Why no database?**
   → Simplicity. Future: could add for historical tracking

5. **Why Vercel?**
   → Free, serverless, auto-deploy from GitHub

---

**Last Updated:** March 2026
**Current Version:** Web App with Per-ETF Architecture
**Status:** Production-ready
