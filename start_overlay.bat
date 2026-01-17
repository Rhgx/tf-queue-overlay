@echo off
setlocal enabledelayedexpansion

REM --- Change these if needed ---
set "PY=python"
set "SCRIPT=%~dp0main.py"
set "TITLE=TF2_MATCH_TIMER_OVERLAY"

echo Starting overlay...
start "TF2 Overlay Launcher" /min %PY% "%SCRIPT%"

echo.
echo Overlay started. Press Q then Enter to quit it.
echo (This window can stay minimized if you want.)
echo.

:loop
set /p input="> "
if /i "!input!"=="q" goto quit
if /i "!input!"=="quit" goto quit
goto loop

:quit
echo Stopping overlay...

REM Kill any python process that has our window title in its command line.
REM This is safer than killing all python.exe.
for /f "tokens=2 delims=," %%P in ('
  tasklist /v /fo csv ^| findstr /i "%TITLE%"
') do (
  echo Killing PID %%~P
  taskkill /pid %%~P /f >nul 2>&1
)

echo Done.
timeout /t 1 >nul
exit /b 0