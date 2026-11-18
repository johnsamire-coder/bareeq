# Bareeq test link: lets the client try the app from any phone browser.
# Runs the server and the browser version of the app on this laptop, and opens
# a temporary public link (Cloudflare quick tunnel, free, no account).
# The link works only while this window stays open. It changes every time.
#
# Run:  powershell -executionpolicy bypass -file d:\bareeq\scripts\demo-link.ps1
# Add -rebuild after pulling new app changes from GitHub.
param([switch]$Rebuild)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$web = Join-Path $root "mobile\build\web"

# 1) cloudflared
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) {
    foreach ($p in @("C:\Program Files (x86)\cloudflared\cloudflared.exe", "C:\Program Files\cloudflared\cloudflared.exe")) {
        if (Test-Path $p) { $cf = $p }
    }
}
if (-not $cf) {
    Write-Host "cloudflared is not installed. Run: winget install --id cloudflare.cloudflared" -ForegroundColor Red
    exit 1
}

# 2) the browser version of the app (talks to the same address it is opened from)
if ($Rebuild -or -not (Test-Path (Join-Path $web "index.html"))) {
    Write-Host "Building the app (a few minutes the first time)..." -ForegroundColor Cyan
    Push-Location (Join-Path $root "mobile")
    flutter pub get
    flutter build web --release --dart-define=API_BASE=/api
    Pop-Location
}

# 3) the server, in its own window (login codes also show there)
$env:DJANGO_DEBUG = "False"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,.trycloudflare.com"
$env:APP_WEB_DIR = $web
Push-Location $backend
& .\.venv\Scripts\python.exe manage.py migrate --noinput
$server = Start-Process -PassThru -WorkingDirectory $backend -FilePath (Join-Path $backend ".venv\Scripts\python.exe") `
    -ArgumentList "manage.py", "runserver", "127.0.0.1:8000", "--noreload", "--insecure"
Pop-Location

# 4) the public link
$log = Join-Path $env:TEMP "bareeq-tunnel.log"
if (Test-Path $log) { Remove-Item $log }
$tunnel = Start-Process -PassThru -WindowStyle Hidden -FilePath $cf `
    -ArgumentList "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8000" -RedirectStandardError $log
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value }
    }
}
if (-not $url) {
    Write-Host "Could not open the link. Send this file to Claude: $log" -ForegroundColor Red
    Stop-Process -Id $server.Id, $tunnel.Id -ErrorAction SilentlyContinue
    exit 1
}
Set-Clipboard $url
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " Test link (copied, paste it to the client):" -ForegroundColor Green
Write-Host " $url" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Green
Write-Host "Keep this window open. Press Enter here to stop the link."
Read-Host | Out-Null
Stop-Process -Id $server.Id, $tunnel.Id -ErrorAction SilentlyContinue
Write-Host "Stopped."
