$ErrorActionPreference = "Stop"

$python = "C:\PROJETOS IA\FAROL 2700 2707\.venv\Scripts\python.exe"
$scriptName = "Pesquisa Iphone 17 Pro Max Paraguai.py"
$pythonCode = "exec(compile(open(r'$scriptName', encoding='utf-8').read(), r'$scriptName', 'exec'), {'__file__': r'$scriptName', '__name__': '__main__'})"
$logDir = Join-Path $PSScriptRoot "logs"
$logFile = Join-Path $logDir "pesquisa_iphone.log"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Set-Location $PSScriptRoot

Add-Content -Path $logFile -Value ""
Add-Content -Path $logFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Inicio da pesquisa"
& $python -c $pythonCode *>> $logFile
$exitCode = $LASTEXITCODE

exit $exitCode
