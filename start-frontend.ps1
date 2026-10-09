$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'frontend')
$bundledNode = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$nodePath = (Get-Command node -ErrorAction SilentlyContinue).Source
if ($nodePath) { $version = & $nodePath -p 'process.versions.node'; if ([version]$version -lt [version]'22.12.0') { $nodePath = $null } }
if (-not $nodePath -and (Test-Path -LiteralPath $bundledNode)) { $nodePath = $bundledNode }
if (-not $nodePath) { throw 'Please install Node.js 22.12+ (24 LTS recommended)' }
$env:Path = (Split-Path $nodePath) + ';' + $env:Path
if (-not (Test-Path 'node_modules/@dcloudio/vite-plugin-uni/bin/uni.js')) {
  npm.cmd install
  if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
}
& $nodePath 'node_modules/@dcloudio/vite-plugin-uni/bin/uni.js' --host 0.0.0.0
