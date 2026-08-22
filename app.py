import os
import asyncio
from aiohttp import web
from telegram.ext import Application
from config import settings
from db import Database
from bot import register_handlers
from scheduler import start_scheduler
import urllib.parse
import hmac
import hashlib
import json

def verify_init_data(telegram_init_data: str, bot_token: str):
    parsed_data = dict(urllib.parse.parse_qsl(telegram_init_data))
    hash_ = parsed_data.pop('hash', None)
    if not hash_:
        return None
    
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash == hash_:
        user_str = parsed_data.get('user', '{}')
        try:
            return json.loads(user_str)
        except:
            return None
    return None

async def handle_webapp(request):
    with open('webapp.html', 'r', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def api_add_position(request):
    try:
        data = await request.json()
        init_data = data.get('initData')
        
        user_data = verify_init_data(init_data, settings.telegram_bot_token)
        if not user_data:
            return web.json_response({'status': 'error', 'message': 'Xác thực thất bại'}, status=403)
            
        user_id = user_data.get('id')
        symbol = data['symbol']
        qty = int(data['qty'])
        entry = float(data['entry'])
        date_str = data.get('date') # Format: YYYY-MM-DDTHH:MM
        note = data.get('note', '')
        
        bought_at = date_str.replace('T', ' ') if date_str else ''
        
        db = request.app['db']
        pid = db.add_position(user_id, symbol, qty, entry, bought_at, note)
        db.set_tracking(pid, True)
        
        # Send confirmation message via Telegram
        bot_app = request.app['bot_app']
        await bot_app.bot.send_message(
            chat_id=user_id,
            text=f"✅ Đã lưu và bật theo dõi qua Mini App: <b>{symbol}</b> (SL: {qty:,} | Giá: {entry:,.2f})",
            parse_mode='HTML'
        )
        
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def main():
    if not settings.telegram_bot_token:
        raise RuntimeError('Missing TELEGRAM_BOT_TOKEN')
    
    db = Database(settings.db_path)
    
    async def post_init(application):
        start_scheduler(application, db)
        from telegram import BotCommand, MenuButtonWebApp, WebAppInfo
        
        # RENDER_EXTERNAL_URL is provided by Render, e.g., https://stock-monitor.onrender.com
        webapp_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://stock-monitor-bot-g9rm.onrender.com')
        application.bot_data['webapp_url'] = webapp_url
        
        await application.bot.set_my_commands([
            BotCommand("report", "Phân tích báo cáo chủ động"),
            BotCommand("add", "Thêm vị thế (Mở Mini App)"),
            BotCommand("list", "Xem danh mục đang theo dõi")
        ])
        
        from telegram import MenuButtonDefault
        await application.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        
    app = Application.builder().token(settings.telegram_bot_token).post_init(post_init).build()
    register_handlers(app, db)
    
    print('Stock Monitor Bot started')

    # Setup aiohttp web server
    webapp = web.Application()
    webapp['db'] = db
    webapp['bot_app'] = app
    webapp.router.add_get('/', handle_webapp)
    webapp.router.add_post('/api/add', api_add_position)
    
    runner = web.AppRunner(webapp)
    await runner.setup()
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Run bot polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep the asyncio loop running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
