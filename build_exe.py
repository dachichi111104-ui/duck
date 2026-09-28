"""
Script đóng gói ứng dụng DuckCare AI Desktop thành file .exe chạy độc lập.
Thực thi: python build_exe.py
"""
import subprocess
import sys
from pathlib import Path

def build():
    print("=== BAT DAU DONG GOI DUCKCARE AI DESKTOP (.EXE) ===")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=DuckCare_AI",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--add-data=app;app",
        "--add-data=duckai_package;duckai_package",
        "main.py"
    ]
    print("Running PyInstaller command:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n=== DONG GOI THANH CONG! ===")
        print("Thu muc ung dung nam tai: dist/DuckCare_AI/")
        print("Nguoi dung chi can nen (zip) thu muc dist/DuckCare_AI va gui di.")
        print("Nguoi nhan giai nen va nhap doi file DuckCare_AI.exe la chay ngay!")
    else:
        print("\n=== DONG GOI THAT BAI ===")

if __name__ == "__main__":
    build()
