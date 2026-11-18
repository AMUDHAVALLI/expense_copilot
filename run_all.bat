@echo off
title Expense Copilot Launcher
echo ==============================================
echo Launching Expense Copilot Backend and Frontend...
echo ==============================================

start "Expense Copilot Backend" cmd /c "%~dp0run_backend.bat"
start "Expense Copilot Frontend" cmd /c "%~dp0run_frontend.bat"

echo Both servers started!
echo Frontend will be accessible at: http://localhost:5173
echo Backend API docs available at: http://127.0.0.1:8000/docs

