@echo off
title FraudShield AI - Real-Time Fraud Detection Platform
color 0b
echo =====================================================================
echo                FRAUDSHIELD AI - STARTING PLATFORM
echo =====================================================================
echo.
echo [1/2] Opening dashboard in your default browser...
start "" http://127.0.0.1:8000/ui/
echo [2/2] Starting FraudShield AI server on http://127.0.0.1:8000...
echo.
echo Dashboard UI: http://127.0.0.1:8000/ui/
echo Swagger API: http://127.0.0.1:8000/docs
echo.
echo Press Ctrl+C in this window anytime to stop the server.
echo.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
