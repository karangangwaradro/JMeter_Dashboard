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

REM 2. Create Virtual Environment if missing
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Setting up Python virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [WARN] Could not create venv. Proceeding with system Python...
    )
)

REM 3. Activate Virtual Environment & Install Requirements
echo [2/3] Checking & installing dependencies...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    if exist "requirements.txt" (
        python -m pip install -q --upgrade pip
        pip install -q -r requirements.txt
    )
) else (
    if exist "requirements.txt" (
        python -m pip install -q -r requirements.txt
    )
)

REM 4. Check & configure config\.env (JMETER_HOME & JAVA_HOME interactive setup)
echo [3/3] Verifying environment settings...
python python_files\setup_env.py

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
