import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import asyncio
from telegram.ext import Application
import google.generativeai as genai
from config import settings
from db import Database
from bot import register_handlers
from scheduler import start_scheduler

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

def main():
    if not settings.telegram_bot_token:
        raise RuntimeError('Missing TELEGRAM_BOT_TOKEN')
    
    # Configure Gemini
    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)
        # Bật Google Search cho model để lấy tin tức mới nhất
        model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            tools='google_search_retrieval'
        )
    else:
        model = None

    db = Database(settings.db_path)
    async def post_init(application):
        start_scheduler(application, db, model)
        
    app = Application.builder().token(settings.telegram_bot_token).post_init(post_init).build()
    register_handlers(app, db)
    print('Stock Monitor Bot started')

    # Start dummy web server in a background thread for Render
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app.run_polling()

if __name__ == '__main__':
    main()
