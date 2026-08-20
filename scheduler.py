from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from config import settings
from engine import MonitorEngine


def start_scheduler(app, db, ai_model=None):
    async def run_report(report_type):
        engine = MonitorEngine(db, ai_model=ai_model)
        tracked_positions = db.tracked()
        if not tracked_positions:
            return # Silent if no active positions
            
        for p in tracked_positions:
            try:
                report = await engine.build_report(p, report_type)
                await app.bot.send_message(chat_id=p.user_id, text=report, parse_mode='HTML')
            except Exception as exc:
                await app.bot.send_message(chat_id=p.user_id,
                    text=f'⚠️ Báo cáo {p.symbol} lỗi: {type(exc).__name__}: {exc}')

    scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.timezone))
    
    # 08:45 - Trước phiên sáng
    scheduler.add_job(run_report,
        args=['intraday'],
        trigger=CronTrigger(hour=8, minute=45, day_of_week='mon-fri', timezone=ZoneInfo(settings.timezone)),
        id='morning_report', replace_existing=True)
        
    # 12:45 - Trước phiên chiều
    scheduler.add_job(run_report,
        args=['intraday'],
        trigger=CronTrigger(hour=12, minute=45, day_of_week='mon-fri', timezone=ZoneInfo(settings.timezone)),
        id='afternoon_report', replace_existing=True)
        
    # 15:15 - Sau khi đóng cửa
    scheduler.add_job(run_report,
        args=['end_of_day'],
        trigger=CronTrigger(hour=15, minute=15, day_of_week='mon-fri', timezone=ZoneInfo(settings.timezone)),
        id='eod_report', replace_existing=True)
        
    scheduler.start()
