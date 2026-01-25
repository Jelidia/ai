param()

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Local Voice AI - Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python not found!" -ForegroundColor Red
    exit 1
}
Write-Host "       Found: $pythonVersion" -ForegroundColor Green

# Create venv
Write-Host ""
Write-Host "[2/4] Setting up virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}
Write-Host "       Done" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "[3/4] Installing dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

# Download Vosk models
Write-Host ""
Write-Host "[4/4] Downloading speech models..." -ForegroundColor Yellow
& .\scripts\download_models.ps1

# Create static folder
New-Item -ItemType Directory -Force -Path ".\static" | Out-Null

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Pull AI model: ollama pull qwen2.5:3b" -ForegroundColor White
Write-Host "  2. Run: .\scripts\run_web.bat" -ForegroundColor White
Write-Host "  3. Open: http://127.0.0.1:8765" -ForegroundColor White
Write-Host ""