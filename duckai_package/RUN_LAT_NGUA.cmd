@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP.cmd first. Do not run this demo from inside the ZIP file.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" demo.py --mode lat-ngua
if errorlevel 1 echo Demo failed. Send the error above to the developer.
pause
