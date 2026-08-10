@echo off
setlocal
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Web API dependencies are not installed.
  echo Run: python -m pip install -r requirements-web.txt
  pause
  exit /b 1
)
set "DEBUG_OPTION="
set /p "ENABLE_DEBUG=Show all logs? [y/N]: "
if /i "%ENABLE_DEBUG%"=="y" set "DEBUG_OPTION=--debug-all"
if /i "%ENABLE_DEBUG%"=="yes" set "DEBUG_OPTION=--debug-all"
start "Chat TTRPG GM API" python -u web_api.py %DEBUG_OPTION%
if errorlevel 1 (
  echo Failed to start the Web API.
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000
endlocal
