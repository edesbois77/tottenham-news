import http.server
import socketserver
import os

PORT = 8080

print("=== DIAGNOSTIC INFO ===")
print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir('.'))
print("Port:", PORT)

# Check if key files exist
files_to_check = ['index.html', 'tottenham_live.html', 'tottenham_scanner.py', 'requirements.txt']
for file in files_to_check:
    if os.path.exists(file):
        print(f"✅ {file} exists")
        if file.endswith('.html'):
            with open(file, 'r') as f:
                content = f.read()
                print(f"   {file} size: {len(content)} characters")
    else:
        print(f"❌ {file} missing")

print("========================")

# Create a simple test page
html_content = f"""
<!DOCTYPE html>
<html>
<head><title>Render Test</title></head>
<body>
<h1>Render is Working!</h1>
<p>Time: {__import__('datetime').datetime.now()}</p>
<p>Directory: {os.getcwd()}</p>
<p>Files: {', '.join(os.listdir('.'))}</p>
</body>
</html>
"""

with open('debug.html', 'w') as f:
    f.write(html_content)

print("Starting web server...")
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server ready on port {PORT}")
    httpd.serve_forever()
