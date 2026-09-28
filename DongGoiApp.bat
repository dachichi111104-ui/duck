@echo off
chcp 65001 > NUL
echo === ĐÓNG GÓI TỰ ĐỘNG DUCKCARE AI DESKTOP (.EXE) ===
.\.venv\Scripts\python.exe build_exe.py
pause
