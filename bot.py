from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters)

def register_handlers(app, db):
    app.bot_data['db'] = db
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('list', positions))
    app.add_handler(CommandHandler('add', add_position_menu))
    app.add_handler(CommandHandler('test_report', test_report))
    app.add_handler(CommandHandler('report', report_menu))
    
    # Handler cho các nút bấm tác vụ danh mục (pause, close, analyze)
    app.add_handler(CallbackQueryHandler(callback, pattern=r'^(list|follow|pause|close|analyze):?\d*$'))
    
    # Handler cho bàn phím ảo (Reply Keyboard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

from telegram import ReplyKeyboardMarkup, KeyboardButton

async def start(update, context):
    webapp_url = context.application.bot_data.get('webapp_url', 'https://stock-monitor-bot-g9rm.onrender.com')
    from telegram import WebAppInfo
    
    reply_kb = [
        [KeyboardButton("📊 Phân tích báo cáo")],
        [KeyboardButton("📝 Thêm vị thế", web_app=WebAppInfo(url=webapp_url)), KeyboardButton("📋 Xem danh mục")]
    ]
    
    await update.message.reply_text(
        '📊 <b>Stock Monitor</b>\nChào mừng bạn! Dưới đây là bảng điều khiển nhanh của bạn:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(reply_kb, resize_keyboard=True)
    )

async def handle_text(update, context):
    text = update.message.text
    if text == "📊 Phân tích báo cáo":
        await report_menu(update, context)
    elif text == "📋 Xem danh mục":
        await positions(update, context)
    # Nút "Thêm vị thế" là loại WebAppInfo nên nó không gửi text, nó tự mở app.

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
    
    engine = MonitorEngine(db)
    try:
        report = await engine.build_report(p, 'intraday')
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

async def report_menu(update, context):
    db = context.application.bot_data['db']
    rows = db.tracked(update.effective_user.id)
    if not rows:
        await update.message.reply_text("❌ Bạn chưa có vị thế nào đang theo dõi. Hãy thêm vị thế trước.")
        return
        
    kb = []
    # Create buttons for each stock, 3 per row
    row = []
    for p in rows:
        row.append(InlineKeyboardButton(f"[{p.symbol}]", callback_data=f'analyze:{p.id}'))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
        
    await update.message.reply_text(
        "Vui lòng chọn mã cổ phiếu bạn muốn phân tích:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

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
        
    if action == 'analyze':
        await q.message.reply_text(f"🔄 Đang thu thập dữ liệu và phân tích mã {p.symbol}...")
        from engine import MonitorEngine
        engine = MonitorEngine(db)
        try:
            report = await engine.build_report(p, 'intraday')
            await q.message.reply_text(report, parse_mode='HTML')
        except Exception as e:
            await q.message.reply_text(f"⚠️ Lỗi: {str(e)}")
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
