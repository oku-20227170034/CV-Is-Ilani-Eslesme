@echo off
chcp 65001 >nul
echo ==========================================
echo   Resume Matcher - Official Fresh Install
echo ==========================================
echo.

echo [1/2] Backend baslatiliyor (port 8000)...
start "RM-Backend" cmd /k "cd /d %~dp0apps\backend && .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Frontend baslatiliyor (port 3000)...
start "RM-Frontend" cmd /k "cd /d %~dp0apps\frontend && npm run dev"

echo.
echo ==========================================
echo  Her iki servis baslatildi!
echo  Tarayicida ac: http://localhost:3000
echo ==========================================
echo.
pause
