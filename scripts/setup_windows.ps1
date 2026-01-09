param()

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

Write-Host "== Local Face + Voice AI setup =="

# venv
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Host "[1/3] Creating venv..."
  python -m venv .venv
} else {
  Write-Host "[1/3] venv exists."
}

Write-Host "[2/3] Installing requirements..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "[3/3] Downloading offline speech models (Vosk EN+FR)..."
& .\scripts\download_models.ps1

Write-Host "`nSetup done."
Write-Host "Next:"
Write-Host "  1) Install Ollama (https://ollama.com/download/windows)"
Write-Host "  2) Pull a model:  ollama pull llama3.1:8b"
Write-Host "  3) Run:          .\scripts\run.bat"
