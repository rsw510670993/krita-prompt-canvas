@echo off
setlocal
cd /d "%~dp0"

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "Krita Prompt Canvas" "%~dp0.venv\Scripts\pythonw.exe" -m krita_prompt_canvas
    exit /b 0
)

where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "Krita Prompt Canvas" pythonw.exe -m krita_prompt_canvas
    exit /b 0
)

echo Python was not found. Install Python 3.10 or newer.
echo.
pause
exit /b 1
