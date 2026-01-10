import aiohttp
import asyncio

class TelegramLogger:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async def log_async(self, message):
        if not self.bot_token or not self.chat_id:
            return

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        print(f"[TELEGRAM ERROR] Status: {response.status}")
        except Exception as e:
            print(f"[TELEGRAM ERROR] {e}")

    def log(self, message):
        # Fallback for sync calls (though we prefer async)
        print(f"[TELEGRAM] {message}")
