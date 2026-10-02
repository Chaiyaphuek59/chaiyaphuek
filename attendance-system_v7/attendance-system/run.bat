@echo off
chcp 65001 >nul
title Smart Attendance System
cd /d "%~dp0"

echo ==============================================
echo   Smart Attendance System - Starting...
echo ==============================================
echo.

REM Find Python on this machine
where python >nul 2>nul
if %errorlevel%==0 (
    set "PY=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PY=py"
    ) else (
        echo [ERROR] Python not found on this computer
        echo Please install Python from https://www.python.org/downloads/
        echo and check "Add Python to PATH" during installation
        pause
        exit /b 1
    )
)

%PY% run.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The program stopped unexpectedly
    pause
)
