# Runs the backend/database/dataset/LLM test suite against the hackviz_test database.
# Add -SkipOllama to skip the real-inference tests.
param([switch]$SkipOllama)
Set-Location (Join-Path $PSScriptRoot "..")
$py = "backend\.venv\Scripts\python.exe"
if ($SkipOllama) { & $py -m pytest tests -v -m "not ollama" } else { & $py -m pytest tests -v -s }
