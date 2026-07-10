@echo off
echo Starting AutoApply Dashboard...

:: 1. Navigate to your project folder
cd /d "C:\Users\kalek\OneDrive\Desktop\Projects\AutoApply"

:: 2. Start the Flask Backend in a new window
start "AutoApply Backend" cmd /c "python app.py"

:: 3. Start the Vite Frontend in a new window
start "AutoApply Frontend" cmd /c "cd frontend && npm run dev"

:: 4. Wait a couple of seconds and open the dashboard (Vite runs on 5173)
timeout /t 3 /nobreak > nul
start http://localhost:5173
