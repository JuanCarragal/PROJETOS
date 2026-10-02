@echo off
setlocal
chcp 65001 > nul
cd /d "%~dp0"
"%~dp0..\.venv\Scripts\python.exe" "%~dp0pesquisa_iphone_paraguai.py" >> "%~dp0execucao_log.txt" 2>&1
