$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python.exe "$scriptDir\deploy_backend.py"
