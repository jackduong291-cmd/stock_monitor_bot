from providers import MarketDataProvider
from ai_analyzer import analyze

class MonitorEngine:
    def __init__(self, db, ai_model=None):
        self.db = db
        self.market = MarketDataProvider()
        self.ai_model = ai_model

    async def build_report(self, position, report_type='intraday'):
        snapshot = await self.market.snapshot(position.symbol)
        market_ctx = await self.market.market_context()

        pnl = (snapshot.last_price - position.entry_price) * position.quantity
        roi = (snapshot.last_price / position.entry_price - 1) * 100 if position.entry_price > 0 else 0
        ai_analysis = await analyze(position, snapshot, market_ctx, report_type, self.ai_model)

        return self.format_report(position, snapshot, pnl, roi, ai_analysis, report_type)

    @staticmethod
    def format_report(p, s, pnl, roi, ai, report_type):
        sign = '+' if pnl >= 0 else ''
        title = "GIỮA PHIÊN" if report_type == 'intraday' else "CUỐI NGÀY - DỰ ĐOÁN NGÀY MAI"
        return (f'📊 <b>{p.symbol} — BÁO CÁO {title}</b>\n\n'
                f'Giá: <b>{s.last_price:,.2f}</b>\n'
                f'Entry: {p.entry_price:,.2f}\n'
                f'Số lượng: {p.quantity:,}\n'
                f'P/L: <b>{sign}{pnl:,.0f}</b>\n'
                f'ROI: <b>{sign}{roi:.2f}%</b>\n\n'
                f'🤖 <b>AI</b>\n{ai}')
