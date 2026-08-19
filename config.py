import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    market_api_base_url: str = os.getenv("MARKET_API_BASE_URL", "")
    market_api_key: str = os.getenv("MARKET_API_KEY", "")
    fireant_api_base_url: str = os.getenv("FIREANT_API_BASE_URL", "")
    fireant_api_key: str = os.getenv("FIREANT_API_KEY", "")
    db_path: str = os.getenv("DB_PATH", "data/portfolio.db")
    report_hour: int = int(os.getenv("REPORT_HOUR", "14"))
    report_minute: int = int(os.getenv("REPORT_MINUTE", "50"))
    timezone: str = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh")

settings = Settings()
