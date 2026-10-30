@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY="C:\Users\5\AppData\Local\Programs\Python\Python314\python.exe"
if not exist %PY% set PY=python
%PY% scripts\daily_update.py
exit /b %ERRORLEVEL%
