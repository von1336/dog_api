@echo off
chcp 65001 >nul
echo Dog Images Downloader GUI
echo =========================

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python 3.7+
    pause
    exit /b 1
)

python -c "import requests, customtkinter" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
)

python dog_images_gui.py
pause 