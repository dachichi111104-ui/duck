@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
py -3.11 --version
if errorlevel 1 (
  echo Please install Python 3.11 64-bit with Python Launcher, then run SETUP.cmd again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open RUN_DEMO.cmd to choose a video.
pause
exit /b 0
:failed
echo Setup failed. Keep this window open and send the error text to the developer.
pause
exit /b 1
