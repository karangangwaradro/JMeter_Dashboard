@echo off
cd /d "%~dp0"

echo.
echo =======================================================
echo   ⚡ PerfPilot — Local Performance Testing Platform
echo =======================================================
echo.

REM 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM 2. Create Virtual Environment if missing or incomplete
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Creating Python virtual environment...
    python -m venv venv
)

REM 3. Install dependencies
echo [2/3] Checking dependencies...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    if exist "requirements.txt" (
        pip install -q -r requirements.txt
    )
) else (
    echo [INFO] Running using system Python environment...
    python -m pip install -q -r requirements.txt 2>nul
)

REM 4. Ensure config\.env exists
if not exist "config\.env" (
    echo [3/3] Creating default config\.env...
    copy "config\.env.template" "config\.env" >nul
)

REM 5. Free port 8080 if previously occupied
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /r ":8080 .*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Launching PerfPilot Web Dashboard Server...
echo Web UI will be available at: http://localhost:8080/
echo.

python main.py

pause
