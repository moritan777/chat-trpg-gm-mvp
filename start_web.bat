@echo off
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Web API dependencies are not installed.
  echo Run: python -m pip install -r requirements-web.txt
  pause
  exit /b 1
)
start "Chat TTRPG GM API" python web_api.py
if errorlevel 1 (
  echo Failed to start the Web API.
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000
