@echo off
echo Starting AutoApply Dashboard...

:: 1. Navigate to your project folder
cd "C:\Users\kalek\OneDrive\Desktop\Projects\AutoApply"

:: 2. Open dashboard in default browser
start http://127.0.0.1:5000

:: 3. Run the Flask server
python app.py
