@echo off
title Selfbot AI - Running
echo ==========================================
echo          STARTING SELFBOT
echo ==========================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed! Download it at python.org
    pause
    exit
)

echo Installing libraries...
pip install -r requirements.txt

echo Starting Bot...
python main.py
pause
