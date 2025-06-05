#!/bin/bash
echo "Starting simple HTTP server..."
cd /opt/render/project/src
ls -la
python -m http.server 8080
