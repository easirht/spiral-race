# deploy.ps1 - build, patch canvas CSS, copy to docs
python -m pygbag --build .
Copy-Item -Path build\web\* -Destination docs -Recurse -Force

$css = @'
<style id="fit-fix">
  html, body { margin:0; height:100%; background:#0a1024; overflow:hidden; }
  canvas#canvas {
    position:fixed !important; left:50% !important; top:50% !important;
    transform:translate(-50%,-50%) !important;
    width:min(100vw, calc(100vh * 16 / 9)) !important;
    height:min(100vh, calc(100vw * 9 / 16)) !important;
    max-width:none !important; max-height:none !important;
    margin:0 !important; border:0 !important;
  }
</style>
'@

$p = "docs\index.html"
$html = Get-Content $p -Raw
$html = $html -replace '(?s)<style id="fit-fix">.*?</style>', ''
$html = $html -replace '</head>', ($css + "`n</head>")
Set-Content -Path $p -Value $html -Encoding utf8
Write-Host "Done: docs/index.html patched"