@echo off
chcp 65001 >nul
title Smart Attendance System
cd /d "%~dp0"

echo ==============================================
echo   Smart Attendance System - กำลังเริ่มระบบ
echo ==============================================
echo.

REM หา Python ในเครื่อง
where python >nul 2>nul
if %errorlevel%==0 (
    set "PY=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PY=py"
    ) else (
        echo [ERROR] ไม่พบ Python ในเครื่อง
        echo กรุณาติดตั้ง Python จาก https://www.python.org/downloads/
        echo และติ๊กเลือก "Add Python to PATH" ตอนติดตั้ง
        pause
        exit /b 1
    )
)

%PY% run.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] โปรแกรมหยุดทำงานผิดปกติ
    pause
)
