Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "             FRAUDSHIELD AI - STARTING PLATFORM" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] Opening dashboard in your default browser..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000/ui/"
Write-Host "[2/2] Starting FraudShield AI server on http://127.0.0.1:8000..." -ForegroundColor Yellow
Write-Host "Dashboard UI: http://127.0.0.1:8000/ui/" -ForegroundColor Cyan
Write-Host "Swagger Docs: http://127.0.0.1:8000/docs`n" -ForegroundColor Cyan
Write-Host "Press Ctrl+C anytime to stop the server.`n" -ForegroundColor DarkGray
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
