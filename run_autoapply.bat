@echo off
echo Waking up and starting AutoApply...

:: 1. Navigate to your project folder
cd "C:\Users\kalek\OneDrive\Desktop\AutoApply"

:: 2. Run the main pipeline (which now includes email delivery)
python run.py

:: 3. Pipeline is completely finished (success or fail). Put the PC back to sleep.
echo Pipeline complete. Suspending PC...
rundll32.exe powrprof.dll,SetSuspendState 0,1,0
