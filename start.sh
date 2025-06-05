#!/bin/bash
python -m http.server 8080 --directory . &
python tottenham_scanner.py
