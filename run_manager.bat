@echo off
set "PYTHON_EXE=pythonw.exe"
where %PYTHON_EXE% >nul 2>&1
if %errorlevel% neq 0 set "PYTHON_EXE=python.exe"

echo Launching Privacy Guard Rule Manager (Console-less)...
start "" venv\Scripts\%PYTHON_EXE% -m rule_manager_gui
exit
