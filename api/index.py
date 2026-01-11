from http.server import BaseHTTPRequestHandler
import os

class handler(BaseHTTPRequestHandler):
      def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('SMC Pro Ultra Python Bot is Deployed! Check Vercel Logs for Bot Activity.'.encode('utf-8'))
                return
