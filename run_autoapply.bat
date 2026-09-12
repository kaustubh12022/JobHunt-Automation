@echo off
title AutoApply Launcher
echo ================================================
echo   AutoApply Dashboard Launcher
echo ================================================
echo.

:: 1. Navigate to your project folder
cd /d "%~dp0"
echo [1/3] Working directory: %CD%
echo.

:: Get Local IP Address for Mobile Link
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do set IP=%%A
set IP=%IP: =%

:: 2. Install Python dependencies silently
echo Installing/checking Python packages...
pip install -r requirements.txt -q
echo Done.
echo.

:: 3. Start the Flask Backend in a new persistent window
echo [2/3] Starting Flask Backend (port 5000)...
start "AutoApply Backend" cmd /k "cd /d "%~dp0" && echo === AutoApply Flask Backend === && echo. && python app.py & echo. & echo Backend stopped. Press any key to close. & pause"

:: 3. Start the Vite Frontend in a new persistent window
echo [3/3] Starting Vite Frontend (port 5173)...
start "AutoApply Frontend" cmd /k "cd /d "%~dp0frontend" && echo === AutoApply Vite Frontend === && echo. && npm run dev & echo. & echo Frontend stopped. Press any key to close. & pause"

:: 4. Wait for both servers to be ready, then open browser
echo.
echo Waiting for servers to start...
timeout /t 5 /nobreak > nul

echo Opening dashboard at http://localhost:5173
start http://localhost:5173

echo.
echo ================================================
echo   ✅ Both servers are running!
echo.
echo   💻 FOR YOUR PC:
echo      Frontend: http://localhost:5173
echo      Backend:  http://localhost:5000
echo.
echo   📱 FOR YOUR PHONE (Same WiFi):
echo      Frontend: http://%IP%:5173
echo ================================================
echo.
echo Close the Backend and Frontend windows to stop the servers.
pause
