# 🚀 Voyager HIP-3 Equity Perpetuals Dashboard

A comprehensive Streamlit dashboard for tracking equity perpetuals on Hyperliquid with market data, technicals, derivatives, and options analytics.

## 📊 Features

- **Market Snapshot**: Real-time prices, volume, and price changes across multiple timeframes
- **Technical Analysis**: RSI, MACD, moving averages, and trend indicators
- **Derivatives Intelligence**: Funding rates and market positioning
- **Options Analytics**: Max pain, implied volatility, and skew analysis

## 🎯 Supported Symbols

The dashboard supports 26+ equity perpetuals including:
- **xyz:** XYZ100, TSLA, NVDA, HOOD, INTC, PLTR, COIN, META, AAPL, MSFT, ORCL, GOOGL, AMZN, AMD, MU, SNDK, MSTR, CRCL, NFLX, COST, LLY, SKHX, TSM
- **flx:** CRCL
- **vntl:** MAG7, SEMIS

### File Structure

```
.
├── app.py                   # Main Streamlit application entry point
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── src/                     # Source code modules
│   ├── __init__.py
│   ├── config.py            # Configuration constants
│   ├── data_classes.py      # Data classes
│   ├── utils.py             # Utility functions
│   ├── api.py               # API functions
│   ├── technicals.py        # Technical analysis
│   ├── derivatives.py       # Derivatives functions
│   ├── options.py           # Options functions
│   └── charts.py            # Chart creation functions
└── README.md                # This file
```

## 🛠️ Local Development

### Installation

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## 📝 Notes

- Data is cached for performance (15 minutes for API calls, 1 hour for candles)
- The dashboard fetches data from Hyperliquid API and Yahoo Finance
- Selecting many symbols may slow down loading - start with a few and add more as needed
- Auto-refresh option available in sidebar (5-minute intervals)
