@echo off
setlocal
title Privacy Filter v4.3

echo ==========================================
echo    Privacy Filter Service Starting...
echo ==========================================
echo.

:: 1. Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run "setup.bat" first to initialize the application.
    pause
    exit /b 1
)

:: 2. Launch using virtual environment
echo Launching... (Minimize this window to hide it)
echo Press Alt+F9 to swap between safe/unsafe versions.
echo Press Alt+F10 to open settings.
echo.

venv\Scripts\python main.py

if %errorlevel% neq 0 (
    echo [INFO] Privacy Filter service ended with exit code: %errorlevel%.
)

pause
