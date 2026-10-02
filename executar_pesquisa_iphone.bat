@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0executar_pesquisa_iphone.ps1"
exit /b %ERRORLEVEL%
