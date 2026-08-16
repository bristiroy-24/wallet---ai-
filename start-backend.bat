@echo off
title WalletAI Backend Server
echo ==========================================
echo   WalletAI Backend - Starting...
echo   API Docs: http://localhost:8000/docs
echo   Press Ctrl+C to stop
echo ==========================================
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
