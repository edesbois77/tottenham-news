import http.server
import socketserver
import os

PORT = 8080

# Create a simple HTML file for testing
html_content = """
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<h1>Hello from Render!</h1>
<p>If you can see this, the web server is working.</p>
<p>Current time: """ + str(__import__('datetime').datetime.now()) + """</p>
</body>
</html>
"""

with open('test.html', 'w') as f:
    f.write(html_content)

print(f"Starting server on port {PORT}")
print("Files in directory:", os.listdir('.'))

Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at port {PORT}")
    httpd.serve_forever()
