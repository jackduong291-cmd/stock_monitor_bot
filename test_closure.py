import asyncio

class Application:
    def __init__(self):
        self.bot_data = {}
        self.post_init = None
    
    async def initialize(self):
        if self.post_init:
            await self.post_init(self)

def register_handlers(app, db):
    app.bot_data['db'] = db

async def main():
    model = "FakeModel"
    db = "FakeDB"
    
    app = Application()
    
    async def post_init(application):
        application.bot_data['model'] = model
        print("post_init executed!")
        
    app.post_init = post_init
    register_handlers(app, db)
    
    await app.initialize()
    print("Keys in bot_data:", list(app.bot_data.keys()))

asyncio.run(main())
