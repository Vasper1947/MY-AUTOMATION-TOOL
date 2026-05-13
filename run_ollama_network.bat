@echo off
REM Run Ollama with network access (0.0.0.0:11434)
REM This allows phone/tablet access from same WiFi network

setlocal enabledelayedexpansion

REM Display instructions
echo.
echo ====================================================================
echo  OLLAMA - Network Mode (Phone Access)
echo ====================================================================
echo.
echo  This will start Ollama on 0.0.0.0:11434
echo  Access from phone: http://^{YOUR_PC_IP^}:11434
echo.
echo  To find your PC IP: Open PowerShell and run "ipconfig"
echo.
echo ====================================================================
echo.

REM Set Ollama to listen on all network interfaces
set OLLAMA_HOST=0.0.0.0:11434

REM Start Ollama
echo Starting Ollama with OLLAMA_HOST=%OLLAMA_HOST%...
echo.

ollama serve

pause
