# Starts the React dashboard on http://localhost:5173 (proxies /api to the backend).
. "$PSScriptRoot\_tools.ps1"; Add-ToolPath
Set-Location (Join-Path $PSScriptRoot "..\frontend")
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
