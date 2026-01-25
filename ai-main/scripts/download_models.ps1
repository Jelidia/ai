param(
  [string]$ModelsDir = "$(Resolve-Path "$PSScriptRoot\..\models")"
)

$ErrorActionPreference = "Stop"

function Download-And-Extract($url, $destDir) {
  if (Test-Path $destDir) {
    Write-Host "[OK] Exists: $destDir"
    return
  }

  $zipName = Split-Path $url -Leaf
  $tmpZip = Join-Path $env:TEMP $zipName

  Write-Host "[DL] $url"
  Invoke-WebRequest -Uri $url -OutFile $tmpZip

  Write-Host "[UNZIP] $tmpZip -> $ModelsDir"
  Expand-Archive -Path $tmpZip -DestinationPath $ModelsDir -Force
  Remove-Item $tmpZip -Force

  if (-not (Test-Path $destDir)) {
    # Sometimes the extracted folder name differs; try to find it.
    $base = [System.IO.Path]::GetFileNameWithoutExtension($zipName)
    $maybe = Join-Path $ModelsDir $base
    if (Test-Path $maybe) {
      Rename-Item -Path $maybe -NewName (Split-Path $destDir -Leaf) -Force
    }
  }

  if (Test-Path $destDir) {
    Write-Host "[OK] Ready: $destDir"
  } else {
    Write-Host "[!] Extracted but folder not found at expected path: $destDir"
    Write-Host "    Check contents of: $ModelsDir"
  }
}

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

# Official Vosk model zips (small, offline)
$enUrl = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
$frUrl = "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip"

Download-And-Extract $enUrl (Join-Path $ModelsDir "vosk-model-small-en-us-0.15")
Download-And-Extract $frUrl (Join-Path $ModelsDir "vosk-model-small-fr-0.22")

Write-Host "`nDone."
