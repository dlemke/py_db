@echo off
REM Build a standalone Windows executable for the password manager.
REM Run this from an activated virtual environment with dependencies installed.

REM Install PyInstaller if not already installed
py -m pip install pyinstaller

REM Build one-file, windowed EXE
py -m PyInstaller ^
  --name "SimplePasswordManager" ^
  --onefile ^
  --windowed ^
  main.py

echo.
echo Build complete. The EXE is in the "dist" folder as SimplePasswordManager.exe
echo.


