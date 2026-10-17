@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (python configure.py) else (py -3 configure.py)
pause
