$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $PythonCmd "$ScriptDir\install.py" @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
