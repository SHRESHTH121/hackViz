# Starts the local Ollama server (if not running) and makes sure qwen2.5:3b is available.
. "$PSScriptRoot\_tools.ps1"; Add-ToolPath
try { Invoke-RestMethod http://localhost:11434/api/version -TimeoutSec 2 | Out-Null; Write-Host "Ollama already running" }
catch {
    Write-Host "Starting ollama serve ..."
    Start-Process -FilePath (Get-Command ollama).Source -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}
$models = (Invoke-RestMethod http://localhost:11434/api/tags).models.name
if ($models -notcontains "qwen2.5:3b") { Write-Host "Pulling qwen2.5:3b (~1.9 GB) ..."; ollama pull qwen2.5:3b }
ollama list
