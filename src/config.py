"""
Configuration constants for Voyager Dashboard
"""

# All supported symbols
SYMBOLS = [
    "xyz:XYZ100", "xyz:TSLA", "xyz:NVDA", "xyz:HOOD", "xyz:INTC", "xyz:PLTR",
    "xyz:COIN", "xyz:META", "xyz:AAPL", "xyz:MSFT", "xyz:ORCL", "xyz:GOOGL",
    "xyz:AMZN", "xyz:AMD", "xyz:MU", "xyz:SNDK", "xyz:MSTR", "xyz:CRCL",
    "xyz:NFLX", "xyz:COST", "xyz:LLY", "xyz:SKHX", "xyz:TSM",
    "flx:CRCL",
    "vntl:MAG7", "vntl:SEMIS"
]

# Extract tickers from symbols (remove prefix)
TICKERS = [s.split(":")[-1] for s in SYMBOLS]

# API Configuration
API_URL = "https://api.hyperliquid.xyz/info"
CACHE_TTL_SECONDS = 15 * 60

# Enhanced color palette - Cyberpunk/Neon theme
COLORS = {
    "background": "#0a0a0f",
    "card": "#12121a",
    "card_border": "#1e1e2e",
    "text": "#e4e4e7",
    "text_muted": "#71717a",
    "accent": "#fbbf24",
    "accent_glow": "#f59e0b",
    "green": "#22c55e",
    "green_glow": "#16a34a",
    "red": "#ef4444",
    "red_glow": "#dc2626",
    "blue": "#3b82f6",
    "blue_glow": "#2563eb",
    "purple": "#a855f7",
    "purple_glow": "#9333ea",
    "cyan": "#06b6d4",
    "cyan_glow": "#0891b2",
    "orange": "#f97316",
    "pink": "#ec4899",
    "gray": "#52525b",
    "gray_light": "#a1a1aa",
}

