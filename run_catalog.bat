@echo off
REM Catalog Builder Launcher
REM This batch file launches the interactive catalog builder interface

cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe catalog_builder.py
) else (
    echo ERROR: Local virtual environment Python not found.
    echo Please run "pip install -r requirements.txt" or create the .venv environment first.
)
pause