from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CommandHandler, CallbackQueryHandler, ConversationHandler,
                          MessageHandler, ContextTypes, filters)

SYMBOL, QTY, ENTRY, BOUGHT_AT, NOTE = range(5)


def register_handlers(app, db):
    app.bot_data['db'] = db
    app.add_handler(CommandHandler('start', menu))
    app.add_handler(CommandHandler('menu', menu))
    app.add_handler(CommandHandler('positions', positions))
    app.add_handler(CallbackQueryHandler(callback, pattern=r'^(add|list|follow|pause|close):?\d*$'))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add, pattern=r'^add$')],
        states={
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, symbol)],
            QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, qty)],
            ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, entry)],
            BOUGHT_AT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bought_at)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, note)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]))

async def menu(update, context):
    kb = [[InlineKeyboardButton('➕ Thêm vị thế', callback_data='add')],
          [InlineKeyboardButton('📋 Danh mục', callback_data='list')]]
    target = update.message or update.callback_query.message
    await target.reply_text('📊 <b>Stock Monitor</b>\nBot chỉ theo dõi, không đặt lệnh.',
                            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

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

async def start_add(update, context):
    await update.callback_query.answer()
    context.user_data.clear()
    await update.callback_query.message.reply_text('Nhập mã cổ phiếu, ví dụ PVS:')
    return SYMBOL

async def symbol(update, context):
    s = update.message.text.strip().upper()
    if not s.isalnum() or len(s) > 10:
        await update.message.reply_text('Mã không hợp lệ.')
        return SYMBOL
    context.user_data['symbol'] = s
    await update.message.reply_text('Nhập số lượng cổ:')
    return QTY

async def qty(update, context):
    try:
        q = int(update.message.text.replace(',', '').strip())
        if q <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text('Số lượng không hợp lệ.')
        return QTY
    context.user_data['qty'] = q
    await update.message.reply_text('Nhập giá entry:')
    return ENTRY

async def entry(update, context):
    try:
        x = float(update.message.text.replace(',', '').strip())
        if x <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text('Giá entry không hợp lệ.')
        return ENTRY
    context.user_data['entry'] = x
    await update.message.reply_text('Nhập thời gian mua (YYYY-MM-DD HH:MM), hoặc - để dùng thời điểm hiện tại:')
    return BOUGHT_AT

async def bought_at(update, context):
    text = update.message.text.strip()
    if text == '-':
        value = datetime.now().isoformat(timespec='minutes')
    else:
        try:
            value = datetime.strptime(text, '%Y-%m-%d %H:%M').isoformat(timespec='minutes')
        except ValueError:
            await update.message.reply_text('Sai định dạng. Ví dụ 2026-08-19 09:30')
            return BOUGHT_AT
    context.user_data['bought_at'] = value
    await update.message.reply_text('Ghi chú/lý do mua (hoặc -):')
    return NOTE

async def note(update, context):
    db = context.application.bot_data['db']
    d = context.user_data
    note_text = '' if update.message.text.strip() == '-' else update.message.text.strip()
    pid = db.add_position(update.effective_user.id, d['symbol'], d['qty'], d['entry'], d['bought_at'], note_text)
    kb = [[InlineKeyboardButton('📈 BẮT ĐẦU THEO DÕI', callback_data=f'follow:{pid}')]]
    await update.message.reply_text(f'Đã tạo {d["symbol"]}. Bot chưa hoạt động cho mã này.',
                                    reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text('Đã hủy.')
    return ConversationHandler.END

async def callback(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == 'add':
        return await start_add(update, context)
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
