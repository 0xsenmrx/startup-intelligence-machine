@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Startup Intelligence Machine v4.1 Launcher
echo ============================================
echo.

:: Check if Python exists
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo Install from: https://python.org 
    pause
    exit /b 1
)

:: Create virtual environment if missing
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment found
)

:: Activate it
echo [2/4] Activating environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo [3/4] Installing dependencies...
pip install -q pydantic google-genai tenacity ddgs rich
if errorlevel 1 (
    echo [WARNING] Some packages may have failed, continuing...
)

:: Check for .env file first, then fallback to environment
echo [4/4] Checking API credentials...
if exist ".env" (
    for /f "tokens=1,* delims==" %%a in (.env) do (
        set %%a=%%b
    )
    echo [OK] API key loaded from .env file
) else (
    if "%GEMINI_API_KEY%"=="" (
        echo.
        echo [!] WARNING: No API key found!
        echo [!] Create a .env file with: GEMINI_API_KEY=your_key_here
        echo [!] Or set environment variable: set GEMINI_API_KEY=your_key
        echo [!] Get one free at: https://aistudio.google.com/app/apikey 
        pause
        exit /b 1
    ) else (
        echo [OK] API key found in environment
    )
)

echo.
echo ============================================
echo  All systems ready. Starting...
echo ============================================
echo.

:: Check for queries.txt to determine mode
if exist "queries.txt" (
    echo [Mode: BATCH - Processing queries.txt]
    python runner.py --mode=batch
) else (
    echo [Mode: EXPLORE - Interactive mode]
    python runner.py --mode=explore
)

:: Keep window open
echo.
echo ============================================
echo  Session Complete
echo ============================================
pause
