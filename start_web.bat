@echo off
start "Chat TTRPG GM API" python web_api.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000
