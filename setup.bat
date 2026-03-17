@echo off
title BankAssist - First Time Setup
color 0B
echo.
echo  ============================================================
echo    BankAssist AI - First Time Setup
echo  ============================================================
echo.

echo  [IMPORTANT] OCR Setup for Scanned PDFs
echo  ============================================================
echo  To support scanned PDFs, you need to install Tesseract-OCR:
echo.
echo  1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
echo  2. Install using default path: C:\Program Files\Tesseract-OCR
echo  3. Return here and continue setup
echo.
set /p continue="Press Enter to continue with setup: "

echo.
echo  [1/4] Installing Python packages...
cd /d "%~dp0backend"
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )

echo.
echo  [2/4] Pulling Ollama LLM model (llama3.2)...
echo  This may take 5-15 minutes on first run (download ~2GB)
ollama pull llama3.2
if errorlevel 1 ( echo [WARNING] Failed to pull llama3.2. Try manually: ollama pull llama3.2 )

echo.
echo  [3/4] Pulling embedding model (nomic-embed-text)...
ollama pull nomic-embed-text
if errorlevel 1 ( echo [WARNING] Failed to pull nomic-embed-text. Try manually. )

echo.
echo  ============================================================
echo    Setup complete! 
echo    Run start.bat to launch the server.
echo  ============================================================
pause
