@echo off
REM ============================================
REM Frontend Build/Start Script (Windows)
REM ============================================

setlocal

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo ITOps Platform Frontend Setup

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo Node.js not found! Please install Node.js 18+
    exit /b 1
)

echo Node version: %NODE_VERSION%

set "ACTION=%~1"
if "%ACTION%"=="" set ACTION=dev

if "%ACTION%"=="install" (
    echo Installing dependencies...
    call npm install
) else if "%ACTION%"=="dev" (
    echo Starting development server...
    call npm run dev
) else if "%ACTION%"=="build" (
    echo Building for production...
    call npm install
    call npm run build
    echo Build complete!
) else (
    echo Usage: run.bat {install^|dev^|build}
)

endlocal