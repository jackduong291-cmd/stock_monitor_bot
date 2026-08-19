from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CommandHandler, CallbackQueryHandler, ConversationHandler,
                          MessageHandler, ContextTypes, filters)

SELECTING_FIELD, TYPING_FIELD = range(2)

def register_handlers(app, db):
    app.bot_data['db'] = db
    app.add_handler(CommandHandler('start', menu))
    app.add_handler(CommandHandler('menu', menu))
    app.add_handler(CommandHandler('list', positions))
    
    # Handler cho các nút bấm tác vụ danh mục (pause, close)
    app.add_handler(CallbackQueryHandler(callback, pattern=r'^(list|follow|pause|close):?\d*$'))
    
    # Form điền thông tin thêm vị thế
    app.add_handler(ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_form, pattern=r'^add$'),
            CommandHandler('add', start_form)
        ],
        states={
            SELECTING_FIELD: [
                CallbackQueryHandler(select_field, pattern=r'^field_(symbol|qty|entry|date|note)$'),
                CallbackQueryHandler(save_form, pattern=r'^save_form$'),
                CallbackQueryHandler(cancel_form, pattern=r'^cancel_form$')
            ],
            TYPING_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_field_text)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_form)]
    ))

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

def get_form_keyboard(data):
    s = data.get('symbol') or 'Chưa nhập'
    q = data.get('qty') or 'Chưa nhập'
    e = data.get('entry') or 'Chưa nhập'
    d = data.get('date') or 'Hôm nay'
    n = data.get('note') or 'Trống'
    
    kb = [
        [InlineKeyboardButton(f'🏷 Mã: {s}', callback_data='field_symbol'),
         InlineKeyboardButton(f'📦 SL: {q}', callback_data='field_qty')],
        [InlineKeyboardButton(f'💲 Giá: {e}', callback_data='field_entry'),
         InlineKeyboardButton(f'📅 Ngày: {d}', callback_data='field_date')],
        [InlineKeyboardButton(f'📝 Ghi chú: {n}', callback_data='field_note')],
        [InlineKeyboardButton('💾 LƯU THÔNG TIN & BẮT ĐẦU', callback_data='save_form')],
        [InlineKeyboardButton('❌ Hủy', callback_data='cancel_form')]
    ]
    return InlineKeyboardMarkup(kb)

async def start_form(update, context):
    if update.callback_query:
        await update.callback_query.answer()
    
    context.user_data['form'] = {
        'symbol': None,
        'qty': None,
        'entry': None,
        'date': 'Hôm nay',
        'note': None
    }
    
    text = "📝 **TẠO VỊ THẾ MỚI**\nBấm vào các nút bên dưới để điền thông tin:"
    markup = get_form_keyboard(context.user_data['form'])
    
    if update.callback_query:
        msg = await update.callback_query.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)
    else:
        msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)
        
    context.user_data['form_msg_id'] = msg.message_id
    return SELECTING_FIELD

async def select_field(update, context):
    query = update.callback_query
    await query.answer()
    field = query.data.split('_')[1]
    context.user_data['current_field'] = field
    
    prompts = {
        'symbol': 'Nhập mã cổ phiếu (VD: PVS):',
        'qty': 'Nhập số lượng cổ phiếu (VD: 1000):',
        'entry': 'Nhập giá mua (VD: 35.5):',
        'date': 'Nhập ngày mua (YYYY-MM-DD HH:MM) hoặc gõ "-" để lấy thời điểm hiện tại:',
        'note': 'Nhập ghi chú cho vị thế này (hoặc gõ "-" để bỏ qua):'
    }
    
    ask_msg = await query.message.reply_text(f"👉 {prompts[field]}")
    context.user_data['ask_msg_id'] = ask_msg.message_id
    return TYPING_FIELD

async def receive_field_text(update, context):
    text = update.message.text.strip()
    field = context.user_data.get('current_field')
    form_data = context.user_data['form']
    
    error = None
    if field == 'symbol':
        if not text.isalnum() or len(text) > 10:
            error = "Mã không hợp lệ."
        else:
            form_data['symbol'] = text.upper()
    elif field == 'qty':
        try:
            q = int(text.replace(',', ''))
            if q <= 0: raise ValueError
            form_data['qty'] = f"{q:,}"
        except:
            error = "Số lượng không hợp lệ."
    elif field == 'entry':
        try:
            e = float(text.replace(',', ''))
            if e <= 0: raise ValueError
            form_data['entry'] = f"{e:,.2f}"
        except:
            error = "Giá mua không hợp lệ."
    elif field == 'date':
        if text == '-':
            form_data['date'] = 'Hôm nay'
        else:
            try:
                datetime.strptime(text, '%Y-%m-%d %H:%M')
                form_data['date'] = text
            except:
                error = "Định dạng ngày không hợp lệ. VD: 2026-08-19 09:30"
    elif field == 'note':
        form_data['note'] = '' if text == '-' else text

    # Xóa tin nhắn rác
    try:
        await update.message.delete()
        if 'ask_msg_id' in context.user_data:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['ask_msg_id'])
    except:
        pass

    if error:
        ask_msg = await update.message.reply_text(f"❌ {error} Vui lòng nhập lại:")
        context.user_data['ask_msg_id'] = ask_msg.message_id
        return TYPING_FIELD
    
    markup = get_form_keyboard(form_data)
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=update.message.chat_id,
            message_id=context.user_data['form_msg_id'],
            reply_markup=markup
        )
    except:
        pass

    return SELECTING_FIELD

async def save_form(update, context):
    query = update.callback_query
    form = context.user_data.get('form', {})
    
    if not form.get('symbol') or not form.get('qty') or not form.get('entry'):
        await query.answer("⚠️ Bạn phải điền đủ Mã, SL và Giá!", show_alert=True)
        return SELECTING_FIELD
        
    await query.answer()
    db = context.application.bot_data['db']
    
    bought_at = datetime.now().isoformat(timespec='minutes') if form['date'] == 'Hôm nay' else datetime.strptime(form['date'], '%Y-%m-%d %H:%M').isoformat(timespec='minutes')
    note_val = form['note'] if form['note'] else ''
    
    qty = int(form['qty'].replace(',', ''))
    entry = float(form['entry'].replace(',', ''))
    
    pid = db.add_position(update.effective_user.id, form['symbol'], qty, entry, bought_at, note_val)
    db.set_tracking(pid, True)
    
    await query.message.edit_text(
        f"✅ Đã lưu và bật theo dõi <b>{form['symbol']}</b> (SL: {form['qty']} | Giá: {form['entry']})",
        parse_mode='HTML'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_form(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text('Đã hủy thêm vị thế.')
    else:
        await update.message.reply_text('Đã hủy.')
    context.user_data.clear()
    return ConversationHandler.END

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
