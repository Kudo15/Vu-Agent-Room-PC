@echo off
setlocal
cd /d "%~dp0"
py -3.13 configure_mail.py
pause
