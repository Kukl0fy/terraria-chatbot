@echo off
title Terraria Chat RAG Presentation Launcher
color 0A
clear

echo =====================================================================
echo  Terraria Chat QA System - Presentation Launcher
echo =====================================================================
echo.

:: 1. Verify/Start Ollama
echo [1/4] Checking if Ollama is running...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo  - Ollama is already running.
) else (
    echo  - Ollama is not running! Starting Ollama...
    start "" "%USERPROFILE%\AppData\Local\Programs\Ollama\ollama app.exe"
    echo  - Waiting 5 seconds for Ollama to initialize...
    timeout /t 5 /nobreak >nul
)
echo.

:: 2. Pre-pull models so they load instantly during the presentation
echo [2/4] Verifying and pulling required Ollama models...
echo  - Pulling nomic-embed-text embeddings (~274 MB)...
ollama pull nomic-embed-text
echo.
echo  - Pulling qwen2.5:14b (~9 GB) to ensure it is ready for presentation...
echo    (If already downloaded, this will complete instantly)
ollama pull qwen2.5:14b
echo.

:: 3. Launch Web Browser
echo [3/4] Launching the presentation web interface...
start http://127.0.0.1:5000
echo.

:: 4. Start the Flask application
echo [4/4] Starting the Flask web server...
echo.
echo =====================================================================
echo  Flask Server is starting on http://127.0.0.1:5000
echo  Press Ctrl+C in this terminal window to stop the application.
echo =====================================================================
echo.
python app.py

pause
