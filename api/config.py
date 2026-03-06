"""
ETF Monitor - Centralized Configuration
Single source of truth for ETFs, datapoints, and sources
"""

# ETF Configuration
ETFS = {
    "LU3098954871": {
        "name": "TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc)",
        "short_name": "TEQ",
        "datapoints": {
            "ter": 0.69,
            # Future: "aum": 250.5,  # in millions
            # Future: "inception_date": "2024-01-15"
        }
    },
    "LU3075459852": {
        "name": "Inyova Impact Investing Active Equity Fund UCITS ETF EUR",
        "short_name": "Inyova",
        "datapoints": {
            "ter": 0.95,
        }
    }
}

# Datapoint Definitions (for future extensibility)
DATAPOINT_CONFIG = {
    "ter": {
        "label": "TER",
        "unit": "%",
        "keywords": ['TER', 'Total Expense Ratio', 'Gesamtkostenquote', 'laufende Kosten', 'Kostenquote'],
        "regex": r'(\d+[.,]\d{1,4})\s*(?:%|bps)?',
        "required": True
    },
    # Future datapoints:
    # "aum": {
    #     "label": "Assets Under Management",
    #     "unit": "M€",
    #     "keywords": ['AUM', 'Fondsvermögen', 'Assets Under Management'],
    #     "regex": r'(\d+[.,]?\d*)\s*(?:M€|Mio|Million)',
    #     "required": False
    # }
}

# Source URL Templates
ISIN_TEMPLATES = [
    "https://www.justetf.com/de/etf-profile.html?isin={ISIN}",
    "https://extraetf.com/de/etf-profile/{ISIN}",
    "https://www.finanzfluss.de/informer/etf/{isin_lower}/",
    "https://www.comdirect.de/inf/etfs/{ISIN}",
    "https://www.avl-investmentfonds.de/fonds/details/{ISIN}",
]

# ETF-specific overrides (for sites without ISIN patterns)
SOURCES_OVERRIDE = {
    "LU3098954871": [
        "https://www.onvista.de/etf/TEQ-General-Artificial-Intelligence-EUR-UCITS-ETF-Acc-ETF-LU3098954871",
        "https://de.finance.yahoo.com/quote/TGAI.DE/",
        "https://live.deutsche-boerse.com/etf/teq-general-artificial-intelligence-eur-ucits-etf-acc"
    ],
    "LU3075459852": [
        "https://www.onvista.de/etf/INY-I-IM-IN-ACT-EQ-EXCH-TRADED-ACT-NOM-EUR-ACC-ON-ETF-LU3075459852",
        "https://de.finance.yahoo.com/quote/INY0.DE/",
        "https://live.deutsche-boerse.com/etf/inyova-impact-investing-active-equity-fund-ucits-etf-eur"
    ]
}

def get_etf_config(isin):
    """Get configuration for a specific ETF"""
    return ETFS.get(isin)

def get_all_isins():
    """Get list of all ISINs"""
    return list(ETFS.keys())

def get_sources_for_isin(isin):
    """Generate all source URLs for an ISIN"""
    urls = []

    # Add template-based URLs
    for template in ISIN_TEMPLATES:
        url = template.format(ISIN=isin, isin_lower=isin.lower())
        urls.append(url)

    # Add override URLs
    if isin in SOURCES_OVERRIDE:
        urls.extend(SOURCES_OVERRIDE[isin])

    return urls

def get_datapoint_value(isin, datapoint_key):
    """Get specific datapoint value for an ETF"""
    etf = ETFS.get(isin, {})
    return etf.get('datapoints', {}).get(datapoint_key)
