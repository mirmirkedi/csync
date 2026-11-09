@echo off
rem Windows launcher for csync: lets you type just "csync" in cmd or PowerShell.
setlocal
set "SCRIPT=%~dp0csync"
where uv >nul 2>nul && (uv run --quiet --python 3.10 python -I "%SCRIPT%" %* & exit /b %errorlevel%)
where py >nul 2>nul && (py -3 -I "%SCRIPT%" %* & exit /b %errorlevel%)
where python >nul 2>nul && (python -I "%SCRIPT%" %* & exit /b %errorlevel%)
echo csync needs Python 3.9+ (or uv). Install one and try again. 1>&2
exit /b 1
