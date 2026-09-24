@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Rekap Gaji dan Upah - Mode Review (Python sistem)

if not exist "server.py" goto err_package
if not exist "frontend\dist\index.html" goto err_build
where python >nul 2>nul
if errorlevel 1 goto err_python

if not exist "database" mkdir "database"
if not exist "backup" mkdir "backup"
if not exist "export" mkdir "export"
if not exist "auth" mkdir "auth"

echo Server lokal dijalankan di http://127.0.0.1:8765
echo Jangan tutup jendela ini selama aplikasi dipakai.
echo.
python server.py
if errorlevel 1 goto err_server
goto end

:err_python
echo.
echo [ERROR] Python tidak ditemukan di PATH.
echo Pakai Python 3 dari python.org, atau paket portable lewat jalankan.bat.
pause
goto end

:err_build
echo.
echo [ERROR] Frontend belum dibangun: frontend\dist\index.html tidak ada.
echo Jalankan: cd frontend  lalu  npm install  dan  npm run build
pause
goto end

:err_package
echo.
echo [ERROR] server.py tidak ditemukan. Jalankan file ini dari folder aplikasi.
pause
goto end

:err_server
echo.
echo [ERROR] Server berhenti. Port 8765 mungkin sedang dipakai aplikasi lain.
pause

:end
endlocal
