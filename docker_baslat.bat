@echo off
title Docker Resume Matcher Baslatici
echo ==================================================
echo         DOCKER RESUME MATCHER BASLATICI
echo ==================================================
echo.
echo [1/3] Proje dizinine gidiliyor...
cd /d "c:\Users\aslis\.gemini\antigravity\scratch\Resume-Matcher-Official"

echo [2/3] Docker container'lari baslatiliyor (ilk seferde build alabilir, lutfen bekleyin)...
docker-compose up -d --build

echo [3/3] Tarayici aciliyor...
start http://localhost:3000

echo.
echo ==================================================
echo  Uygulama basariyla baslatildi!
echo  Bu pencereyi kapatabilirsiniz. (5 saniye icinde kapanacak)
echo ==================================================
timeout /t 5 >nul
