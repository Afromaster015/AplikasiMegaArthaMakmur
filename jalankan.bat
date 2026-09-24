@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Rekap Gaji dan Upah - Mega Artha Makmur

if not exist "runtime\python.exe" goto runtime_error
if not exist "server.py" goto package_error
if not exist "frontend\dist\index.html" goto package_error

if not exist "database" mkdir "database"
if not exist "backup" mkdir "backup"
if not exist "export" mkdir "export"
if not exist "auth" mkdir "auth"

runtime\python.exe server.py
if errorlevel 1 goto server_error
goto end

:runtime_error
echo.
echo [ERROR] Runtime Python portable tidak ditemukan.
echo Extract ulang seluruh isi ZIP sebelum menjalankan aplikasi.
pause
goto end

:package_error
echo.
echo [ERROR] Paket aplikasi tidak lengkap.
echo Pastikan jalankan.bat berada di folder hasil extract ZIP.
pause
goto end

:server_error
echo.
echo [ERROR] Server lokal berhenti atau port 8765 sedang digunakan.
echo Tutup jendela aplikasi lain lalu jalankan kembali.
pause

:end
endlocal
