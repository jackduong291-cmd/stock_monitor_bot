from providers import MarketDataProvider
from ai_analyzer import analyze
from datetime import datetime

class MonitorEngine:
    def __init__(self, db):
        self.db = db
        self.market = MarketDataProvider()

    async def build_report(self, position, report_type='intraday'):
        snapshot = await self.market.snapshot(position.symbol)
        market_ctx = await self.market.market_context()

        # Real value in VND
        entry_val = position.entry_price * 1000 * position.quantity
        current_val = snapshot.last_price * 1000 * position.quantity
        
        # Standard VN fees: 0.15% buy fee, 0.25% sell fee + tax. Total 0.4%
        buy_fee = entry_val * 0.0015
        sell_fee = current_val * 0.0025
        
        net_pnl = current_val - sell_fee - (entry_val + buy_fee)
        
        roi = (snapshot.last_price / position.entry_price - 1) * 100 if position.entry_price > 0 else 0
        ai_analysis = await analyze(position, snapshot, market_ctx, report_type)
        if len(ai_analysis) > 3500:
            ai_analysis = ai_analysis[:3500] + '... (Cắt bớt do quá dài)'

        return self.format_report(position, snapshot, net_pnl, roi, ai_analysis, report_type)

    @staticmethod
    def format_report(p, s, pnl, roi, ai, report_type):
        roi_sign = '+' if roi >= 0 else ''
        title = "GIỮA PHIÊN" if report_type == 'intraday' else "CUỐI NGÀY - DỰ ĐOÁN NGÀY MAI"
        return (f'📊 <b>{p.symbol} — BÁO CÁO {title}</b>\n\n'
                f'Giá: <b>{s.last_price:,.2f}</b>\n'
                f'Entry: {p.entry_price:,.2f}\n'
                f'Số lượng: {p.quantity:,}\n'
                f'P/L: <b>{pnl:+,.0f} VNĐ</b>\n'
                f'ROI: <b>{roi_sign}{roi:.2f}%</b>\n\n'
                f'🤖 <b>AI</b>\n{ai}')
