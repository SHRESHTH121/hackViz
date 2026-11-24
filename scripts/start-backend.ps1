# Starts the FastAPI backend on http://127.0.0.1:8000 (creates tables + imports the dataset on first start).
$backend = Join-Path $PSScriptRoot "..\backend"
Set-Location $backend
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
if (-not (Test-Path ".env")) { Write-Error "backend\.env missing - copy .env.example to .env and set DATABASE_URL"; exit 1 }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
