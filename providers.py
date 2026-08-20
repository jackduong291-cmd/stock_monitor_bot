from models import MarketSnapshot, NewsItem
import logging
from datetime import datetime, timedelta
import pandas as pd



class MarketDataProvider:
    async def snapshot(self, symbol: str) -> MarketSnapshot:
        last_price, change_pct, volume, avg_volume_20 = 0.0, 0.0, 0.0, 0.0
        try:
            from vnstock import Vnstock
            today = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
            
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df = stock.quote.history(start=start_date, end=today)
            
            if df is not None and not df.empty:
                last_row = df.iloc[-1]
                # Vnstock 4.x usually returns raw close price (e.g. 36.0 or 36000)
                price_val = float(last_row.get('close', 0))
                last_price = price_val if price_val > 1000 else price_val * 1000
                
                volume = float(last_row.get('volume', 0))
                if len(df) > 1:
                    prev_val = float(df.iloc[-2].get('close', price_val))
                    prev_price = prev_val if prev_val > 1000 else prev_val * 1000
                    if prev_price > 0:
                        change_pct = ((last_price - prev_price) / prev_price) * 100
                avg_volume_20 = float(df['volume'].tail(20).mean()) if len(df) >= 20 else volume
        except Exception as e:
            logging.error(f"Lỗi lấy dữ liệu vnstock cho {symbol}: {e}")

        return MarketSnapshot(
            symbol=symbol,
            last_price=last_price,
            change_pct=change_pct,
            volume=volume,
            avg_volume_20=avg_volume_20,
            indicators={},
            market_context={}
        )

    async def market_context(self) -> dict:
        return {"status": "VNI"}

    async def sector_for(self, symbol: str) -> str:
        return "VN"
