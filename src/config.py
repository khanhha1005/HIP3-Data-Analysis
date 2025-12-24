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

# Light Glassmorphism color palette - Clean and modern
COLORS = {
    "background": "#f8fafc",
    "card": "rgba(255, 255, 255, 0.9)",
    "card_border": "rgba(0, 0, 0, 0.08)",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "accent": "#6366f1",
    "accent_glow": "#818cf8",
    "green": "#10b981",
    "green_glow": "#34d399",
    "red": "#f43f5e",
    "red_glow": "#fb7185",
    "blue": "#3b82f6",
    "blue_glow": "#60a5fa",
    "purple": "#a855f7",
    "purple_glow": "#a78bfa",
    "cyan": "#06b6d4",
    "cyan_glow": "#22d3ee",
    "orange": "#f97316",
    "pink": "#ec4899",
    "gray": "#94a3b8",
    "gray_light": "#cbd5e1",
}

