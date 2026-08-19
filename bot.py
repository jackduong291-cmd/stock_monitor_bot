from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters)

def register_handlers(app, db):
    app.bot_data['db'] = db
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('list', positions))
    
    # Handler cho các nút bấm tác vụ danh mục (pause, close)
    app.add_handler(CallbackQueryHandler(callback, pattern=r'^(list|follow|pause|close):?\d*$'))

async def start(update, context):
    await update.message.reply_text('📊 <b>Stock Monitor</b>\nChào mừng bạn! Hãy bấm vào nút <b>Thêm vị thế</b> ở góc dưới cùng bên trái để mở Bảng điền thông tin nhé.',
                            parse_mode='HTML')

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
