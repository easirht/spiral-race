# deploy.ps1 - build, patch canvas CSS + mobile helpers + share-preview tags, copy to docs
python -m pygbag --build .
Copy-Item -Path build\web\* -Destination docs -Recurse -Force

$meta = @'
<!-- sr-meta -->
<meta name="description" content="Spiral Race: a fast spiral board game. Race to the Core, play vs AI or online with friends. Free in your browser.">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Spiral Race">
<meta property="og:title" content="Spiral Race - Race to the Core">
<meta property="og:description" content="Free browser board game. Play vs AI or online with friends.">
<meta property="og:url" content="https://easirht.github.io/spiral-race/">
<meta property="og:image" content="https://easirht.github.io/spiral-race/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Spiral Race - Race to the Core">
<meta name="twitter:description" content="Free browser board game. Play vs AI or online with friends.">
<meta name="twitter:image" content="https://easirht.github.io/spiral-race/og-image.jpg">
<!-- /sr-meta -->
'@

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
  #rotate-hint { display:none; }
  @media (orientation:portrait) and (max-width:900px) {
    #rotate-hint {
      display:block; position:fixed; top:0; left:0; right:0; z-index:99999;
      padding:14px 12px; text-align:center; pointer-events:none;
      font:600 15px/1.35 system-ui,sans-serif; color:#ffd35a;
      background:rgba(10,16,36,.94);
    }
  }
</style>
'@

$body = @'
<div id="rotate-hint">&#8635; Rotate your phone sideways (landscape) for the best view</div>
<script id="sr-mobile">
(function(){
  var done=false;
  function go(){
    if(done) return; done=true;
    try{
      var el=document.documentElement;
      var p=el.requestFullscreen?el.requestFullscreen():null;
      var lock=function(){ try{ screen.orientation.lock('landscape').catch(function(){}); }catch(e){} };
      if(p&&p.then){ p.then(lock).catch(function(){}); } else { lock(); }
    }catch(e){}
  }
  if(window.matchMedia && window.matchMedia('(pointer: coarse)').matches){
    window.addEventListener('touchend', go, {once:true});
  }
})();
</script>
'@

$p = "docs\index.html"
$html = Get-Content $p -Raw
$html = $html -replace '(?s)<!-- sr-meta -->.*?<!-- /sr-meta -->', ''
$html = $html -replace '(?s)<style id="fit-fix">.*?</style>', ''
$html = $html -replace '(?s)<div id="rotate-hint">.*?</div>\s*<script id="sr-mobile">.*?</script>', ''
$html = $html -replace '</head>', ($meta + "`n" + $css + "`n</head>")
$html = $html -replace '</body>', ($body + "`n</body>")
Set-Content -Path $p -Value $html -Encoding utf8

if (-not (Test-Path "docs\og-image.jpg")) {
  Write-Host "WARNING: docs\og-image.jpg not found - put the preview image there"
}
Write-Host "Done: docs/index.html patched"