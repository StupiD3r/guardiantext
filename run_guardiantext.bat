@echo off
echo Starting GuardianText System...
echo.

REM Start Backend (Flask with Socket.IO)
start "GuardianText Backend" cmd /k "cd /d %~dp0backend && python app.py"

REM Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

REM Start Frontend (opens browser)
echo Opening GuardianText in browser...
start "" "http://localhost:5000"

echo.
echo GuardianText is starting up!
echo Backend: http://localhost:5000
echo Chat Interface: http://localhost:5000/chat.html
echo.
pause
