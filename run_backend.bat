@echo off
title Expense Copilot - FastAPI Backend
cd /d "%~dp0backend"
echo ==============================================
echo Starting Expense Copilot Backend on port 8000...
echo ==============================================
".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause

