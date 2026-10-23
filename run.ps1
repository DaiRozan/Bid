$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "未找到 Python 3.11+，请先安装 Python。" }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "未找到 npm，请先安装 Node.js。" }

if (-not (Test-Path $venvPython)) {
  python -m venv (Join-Path $root ".venv")
}
& $venvPython -m pip install -e "$root\backend[test]" --quiet
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
  npm --prefix "$root\frontend" install
}

$backendPort = 8000
$frontendPort = 5173
$backend = Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "app.main:app", "--app-dir", "$root\backend", "--host", "127.0.0.1", "--port", $backendPort -PassThru -WindowStyle Hidden
try {
  $ready = $false
  for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
      $health = Invoke-RestMethod "http://127.0.0.1:$backendPort/api/health" -TimeoutSec 2
      if ($health.status -eq "ok") { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
  }
  if (-not $ready) { throw "后端未能在预期时间内启动。" }
  Write-Host "技术标生成系统已启动：http://127.0.0.1:$frontendPort" -ForegroundColor Green
  Write-Host "后端健康检查：http://127.0.0.1:$backendPort/api/health"
  npm --prefix "$root\frontend" run dev -- --host 127.0.0.1 --port $frontendPort
} finally {
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}
