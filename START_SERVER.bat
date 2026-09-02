@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title PerfPilot Server

echo.
echo =======================================================
echo   PerfPilot - Local Performance Testing Platform
echo =======================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Setup venv if missing
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Setting up Python virtual environment...
    python -m venv venv
)

:: 3. Select Python Executable
set "PY_EXE=python"
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
)

:: 4. Install Dependencies
echo [2/3] Checking dependencies...
if exist "requirements.txt" (
    "%PY_EXE%" -m pip install -q -r requirements.txt
)

:: 5. Run Environment Setup (JAVA_HOME & JMETER_HOME validator)
echo [3/3] Verifying environment settings...
"%PY_EXE%" python_files\setup_env.py

:: 6. Launch Server
echo.
echo Launching PerfPilot Web Dashboard Server...
echo Web UI will be available at: http://localhost:8080/
echo.

"%PY_EXE%" main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server exited unexpectedly.
    pause
)
