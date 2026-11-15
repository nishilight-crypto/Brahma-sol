# ==============================================================================
# BRAHMA SOL — Automated Production Build & Release Pipeline
# Compiles:
#   1. BrahmaSol.exe Application Payload (PyInstaller)
#   2. Uninstaller integration (Uninstall.exe)
#   3. brahma-sol_setup.exe Setup Wizard (Embedded WebEngine & 3D Companion)
#   4. Mirrors binary to Web Distribution & Updates Cloudflare Worker Hub
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "`n>>> [STEP 1/5] Building Brahma Sol Main Application (BrahmaSol)..." -ForegroundColor Cyan
& .\.venv\Scripts\pyinstaller.exe installer\BrahmaSol_App.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to compile BrahmaSol application!" -ForegroundColor Red
    exit 1
}

Write-Host "`n>>> [STEP 2/5] Bundling Uninstaller and Control Files..." -ForegroundColor Cyan
if (Test-Path "dist\Uninstall.exe") {
    Copy-Item "dist\Uninstall.exe" -Destination "dist\BrahmaSol\Uninstall.exe" -Force
}
if (Test-Path "installer\uninstall.cmd") {
    Copy-Item "installer\uninstall.cmd" -Destination "dist\BrahmaSol\uninstall.cmd" -Force
}

Write-Host "`n>>> [STEP 3/5] Building Standalone Setup Wizard (brahma-sol_setup.exe)..." -ForegroundColor Cyan
& .\.venv\Scripts\pyinstaller.exe installer\BrahmaSol_Setup.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to compile brahma-sol_setup.exe!" -ForegroundColor Red
    exit 1
}

# Note: We distribute the 1.2 GB setup installer via Google Drive CDN rather than Netlify static hosting to stay under Netlify's 50 MB limit.
Write-Host "`n>>> [STEP 4/5] Installer ready at dist\brahma-sol_setup.exe (Google Drive CDN linked)..." -ForegroundColor Cyan

Write-Host "`n>>> [STEP 5/5] Publishing v2.4.0 Release to Cloudflare Update Hub..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -c "
from core.auto_updater import AutoUpdater
res = AutoUpdater.publish_release(
    version='2.4.0',
    download_url='https://drive.google.com/file/d/1V18O0bY4H_e907DiXuheAbOjwZy3ckmQ/view?usp=sharing',
    changelog='Official Release v2.4.0: NASA APOD 4K Desktop Wallpaper Engine, Offline Local Brain Fallback, Brahma Sol Celestial Identity & Support Creator Gated Flow.',
    name='Brahma Sol - Celestial Edition v2.4.0'
)
print('Cloudflare Hub Response:', res)
"

Write-Host "`n==============================================================================" -ForegroundColor Green
Write-Host " BUILD & RELEASE COMPLETE! " -ForegroundColor Green
Write-Host " Installer Output: dist\brahma-sol_setup.exe" -ForegroundColor Green
Write-Host " Web Asset:        $webDownloadDir\brahma-sol_setup.exe" -ForegroundColor Green
Write-Host " Update Edge:       https://brahma-update-hub.brahma-sol.workers.dev/version" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
