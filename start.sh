#!/bin/bash
echo "Starting web server..."
python -c "
import http.server
import socketserver
import threading
import time

def serve():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f'Web server on port {PORT}')
        httpd.serve_forever()

# Start web server
web_thread = threading.Thread(target=serve)
web_thread.start()

print('Web server started, waiting 3 seconds...')
time.sleep(3)

# Start scanner
exec(open('tottenham_scanner.py').read())
"
