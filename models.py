from dataclasses import dataclass
from typing import Optional

@dataclass
class Position:
    id: int
    user_id: int
    symbol: str
    quantity: int
    entry_price: float
    bought_at: str
    note: str
    tracking: bool

@dataclass
class NewsItem:
    id: str
    title: str
    summary: str
    url: str
    published_at: str
    symbol: Optional[str] = None
    sector: Optional[str] = None
    category: str = "market"

@dataclass
class MarketSnapshot:
    symbol: str
    last_price: float
    change_pct: float
    volume: float
    avg_volume_20: float
    indicators: dict
    market_context: dict
