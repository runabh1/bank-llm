@echo off
title BankAssist LLM Server
color 0A
echo.
echo  ============================================================
echo    BankAssist AI - Bank Circular Intelligence System
echo    Starting local server...
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.11+
    echo  Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo  [WARNING] Ollama not found in PATH.
    echo  Download from: https://ollama.ai/download
    echo  Then run: ollama pull llama3.2
    echo  And run:  ollama pull nomic-embed-text
    echo.
    pause
)

:: Get server IP for LAN access info
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set SERVER_IP=%%a
    goto :found
)
:found
set SERVER_IP=%SERVER_IP: =%

echo  [1/4] Installing Python dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo  [2/4] Starting Ollama (if not already running)...
start "" /min ollama serve

timeout /t 3 /nobreak >nul

echo  [3/4] Starting BankAssist server...
echo.
echo  ============================================================
echo    Server running at:
echo      Local:   http://localhost:8000
echo      LAN:     http://%SERVER_IP%:8000
echo      Admin:   http://%SERVER_IP%:8000/admin
echo.
echo    Share the LAN URL with staff on the same network.
echo    Press Ctrl+C to stop the server.
echo  ============================================================
echo.

python main.py

pause
