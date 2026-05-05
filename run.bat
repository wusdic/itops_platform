@echo off
REM ============================================
REM ITOps Platform Startup Script (Windows)
REM ============================================

setlocal

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo   ITOps Platform - Starting...
echo ==========================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.11+
    exit /b 1
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies if needed
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install --upgrade pip
    pip install -r requirements.txt
)

REM Create necessary directories
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "reports" mkdir reports

REM Check configuration
if not exist "config\dev.yaml" (
    if not exist "config\prod.yaml" (
        echo Warning: No configuration file found.
        if exist "config\templates\dev.yaml" (
            copy config\templates\dev.yaml config\dev.yaml
            echo Please edit config\dev.yaml before starting.
        )
        exit /b 1
    )
)

REM Parse command line arguments
set "MODE=%~1"
set "PORT=%~2"
if "%MODE%"=="" set MODE=dev
if "%PORT%"=="" set PORT=8000

REM Export configuration
set "CONFIG_FILE=config\%MODE%.yaml"

echo Starting in %MODE% mode on port %PORT%...
echo.

REM Start the application
python -m uvicorn api.main:app --host 0.0.0.0 --port %PORT% --reload

endlocal