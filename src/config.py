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

# Neon Glassmorphism color palette - Dark with vibrant accents
COLORS = {
    "background": "#0f0f23",
    "card": "rgba(255, 255, 255, 0.05)",
    "card_border": "rgba(255, 255, 255, 0.1)",
    "text": "#ffffff",
    "text_muted": "#a0a0b8",
    "accent": "#00d4ff",
    "accent_glow": "#00a8cc",
    "green": "#00ff88",
    "green_glow": "#00cc6a",
    "red": "#ff3366",
    "red_glow": "#cc1a3d",
    "blue": "#3b82f6",
    "blue_glow": "#2563eb",
    "purple": "#a855f7",
    "purple_glow": "#9333ea",
    "cyan": "#00d4ff",
    "cyan_glow": "#00a8cc",
    "orange": "#ff6b35",
    "pink": "#ec4899",
    "gray": "#64748b",
    "gray_light": "#94a3b8",
}

