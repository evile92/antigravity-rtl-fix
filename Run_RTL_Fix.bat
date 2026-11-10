@echo off
chcp 65001 >nul
title Antigravity RTL Fix
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0antigravity_rtl_fix.py" %*
    goto end
)
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0antigravity_rtl_fix.py" %*
    goto end
)
echo [STOP] Python is not installed. Install it from https://www.python.org/downloads/
:end
echo.
pause
