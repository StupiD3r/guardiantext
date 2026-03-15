@echo off
REM GuardianText – one-click launcher (Windows)
REM Double-click this file to start the server and open your browser.

setlocal

REM Change to the directory where this script lives
cd /d "%~dp0"

echo.
echo Starting GuardianText backend server...

REM Start the Flask/Socket.IO app in a new window
start "" python "%~dp0backend\app.py"

REM Give the server a few seconds to start
timeout /t 3 /nobreak >nul

REM Open the app in the default browser
start "" "http://localhost:5000"

echo.
echo GuardianText should now be available at http://localhost:5000
echo You can close this window; the server is running in a separate window.

endlocal

