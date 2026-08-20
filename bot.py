from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters)

def register_handlers(app, db):
    app.bot_data['db'] = db
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('list', positions))
    app.add_handler(CommandHandler('add', add_position_menu))
    app.add_handler(CommandHandler('test_report', test_report))
    
    # Handler cho các nút bấm tác vụ danh mục (pause, close)
    app.add_handler(CallbackQueryHandler(callback, pattern=r'^(list|follow|pause|close):?\d*$'))

async def start(update, context):
    webapp_url = context.application.bot_data.get('webapp_url', 'https://stock-monitor-bot-g9rm.onrender.com')
    from telegram import WebAppInfo
    kb = [[InlineKeyboardButton('📝 Mở Bảng Điền Thông Tin', web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        '📊 <b>Stock Monitor</b>\nChào mừng bạn! Hãy bấm vào nút bên dưới (hoặc nút Menu góc trái) để mở Bảng điền thông tin nhé.',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def add_position_menu(update, context):
    webapp_url = context.application.bot_data.get('webapp_url', 'https://stock-monitor-bot-g9rm.onrender.com')
    from telegram import WebAppInfo
    kb = [[InlineKeyboardButton('📝 Mở Bảng Điền Thông Tin', web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        'Bấm vào đây để điền thông tin vị thế mới:',
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def test_report(update, context):
    await update.message.reply_text("🔄 Đang tạo báo cáo thử nghiệm, vui lòng đợi 5-10 giây...")
    db = context.application.bot_data['db']
    ai_model = context.application.bot_data.get('model')
    
    rows = db.tracked(update.effective_user.id)
    if not rows:
        await update.message.reply_text("❌ Bạn chưa có vị thế nào đang theo dõi để test.")
        return
        
    p = rows[0] # Test the first one
    from config import settings
    from engine import MonitorEngine
    key_len = len(settings.gemini_api_key) if settings.gemini_api_key else 0
    
    engine = MonitorEngine(db)
    try:
        report = await engine.build_report(p, 'intraday')
        # Bỏ phần in debug đi cho báo cáo sạch sẽ
        await update.message.reply_text(report, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"⚠️ Lỗi: {str(e)}")

async def positions(update, context):
    db = context.application.bot_data['db']
    rows = db.tracked(update.effective_user.id)
    if not rows:
        await update.message.reply_text('Chưa có vị thế đang theo dõi.')
        return
    for p in rows:
        kb = [[InlineKeyboardButton('⏸ Tạm dừng', callback_data=f'pause:{p.id}'),
               InlineKeyboardButton('❌ Đóng', callback_data=f'close:{p.id}')]]
        await update.message.reply_text(
            f'📌 <b>{p.symbol}</b>\nSố lượng: {p.quantity:,}\nEntry: {p.entry_price:,.2f}\n🟢 Đang theo dõi',
            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

async def callback(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == 'list':
        return await positions(update, context)
    
    action, pid = q.data.split(':')
    db = context.application.bot_data['db']
    p = db.get(int(pid))
    if not p or p.user_id != update.effective_user.id:
        await q.message.reply_text('Không tìm thấy vị thế.')
        return
    if action == 'follow':
        db.set_tracking(p.id, True)
        msg = f'🟢 Đã bắt đầu theo dõi {p.symbol}.'
    elif action == 'pause':
        db.set_tracking(p.id, False)
        msg = f'⏸ Đã tạm dừng {p.symbol}.'
    else:
        db.set_tracking(p.id, False)
        msg = f'🔴 Đã đóng theo dõi {p.symbol}.'
    await q.message.reply_text(msg)
