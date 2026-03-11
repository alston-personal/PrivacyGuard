@echo off
setlocal enabledelayedexpansion
title Privacy Filter - Setup

echo ==========================================
echo    Privacy Filter Environment Setup
echo ==========================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: 2. Create Virtual Environment
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [DONE] Virtual environment created.
) else (
    echo [1/3] Virtual environment already exists. Skipping...
)

:: 3. Install Dependencies
echo [2/3] Installing/Updating dependencies...
venv\Scripts\python -m pip install --upgrade pip >nul
venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [DONE] Dependencies installed.

:: 4. Download SpaCy Model
echo [3/3] Downloading Chinese NLP model (zh_core_web_sm)...
venv\Scripts\python -m spacy download zh_core_web_sm
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download SpaCy model.
    pause
    exit /b 1
)
echo [DONE] Model downloaded.

echo.
echo ==========================================
echo    Setup Completed Successfully!
echo ==========================================
echo.
echo You can now use "run_filter.bat" to start the application.
echo.
pause
