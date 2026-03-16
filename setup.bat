@echo off
title BankAssist - First Time Setup
color 0B
echo.
echo  ============================================================
echo    BankAssist AI - First Time Setup
echo  ============================================================
echo.

echo  [1/3] Installing Python packages...
cd /d "%~dp0backend"
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )

echo.
echo  [2/3] Pulling Ollama LLM model (llama3.2)...
echo  This may take 5-15 minutes on first run (download ~2GB)
ollama pull llama3.2
if errorlevel 1 ( echo [WARNING] Failed to pull llama3.2. Try manually: ollama pull llama3.2 )

echo.
echo  [3/3] Pulling embedding model (nomic-embed-text)...
ollama pull nomic-embed-text
if errorlevel 1 ( echo [WARNING] Failed to pull nomic-embed-text. Try manually. )

echo.
echo  ============================================================
echo    Setup complete! 
echo    Run start.bat to launch the server.
echo  ============================================================
pause
