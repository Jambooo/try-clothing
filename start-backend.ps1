$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'backend')
if (-not (Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv }
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
& '.venv/Scripts/alembic.exe' upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
& '.venv/Scripts/python.exe' -m uvicorn app:app --host 0.0.0.0 --port 8000
