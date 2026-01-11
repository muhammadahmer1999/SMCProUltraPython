from http.server import BaseHTTPRequestHandler
import asyncio
import os
import sys

# Add parent directory to path to find main_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_bot import run_cycle

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        # Run one cycle of the bot
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_cycle())
            self.wfile.write(f"Bot Cycle Completed:\n{result}".encode('utf-8'))
        except Exception as e:
            self.wfile.write(f"Error running bot cycle: {str(e)}".encode('utf-8'))
        return
