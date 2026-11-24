# Shared helper: locate node / ollama even if they are not on PATH
# (falls back to portable copies in %LOCALAPPDATA%\hackviz-tools). Does not modify the system PATH.
function Add-ToolPath {
    $tools = Join-Path $env:LOCALAPPDATA "hackviz-tools"
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        $n = Get-ChildItem $tools -Directory -Filter "node-v*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($n) { $env:Path = "$($n.FullName);$env:Path" }
    }
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        foreach ($p in @("$tools\ollama", "$env:LOCALAPPDATA\Programs\Ollama")) {
            if (Test-Path "$p\ollama.exe") { $env:Path = "$p;$env:Path"; break }
        }
    }
    if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
        $pg = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
        if ($pg) { $env:Path = "$($pg.FullName)\bin;$env:Path" }
    }
}
