@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 configure.py --if-needed
if errorlevel 1 goto failed
py -3 room.py
goto end
:usepython
python configure.py --if-needed
if errorlevel 1 goto failed
python room.py
goto end
:failed
echo Setup failed. Read the error above.
:end
pause
