param(
  [Parameter(Mandatory = $true)]
  [string]$OutputDir,
  [Parameter(Mandatory = $true)]
  [string]$EvidenceDir,
  [string]$CacheDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$LauncherDir = Split-Path -Parent $PSScriptRoot
$PackageJsonPath = Join-Path $LauncherDir "package.json"
$PackageMetadata = Get-Content -Raw -Path $PackageJsonPath | ConvertFrom-Json
$Packaging = $PackageMetadata.sentinelPackaging
if ($null -eq $Packaging) {
  throw "sentinelPackaging metadata is required"
}

$ElectronVersion = [string]$Packaging.electronVersion
$ExpectedSha256 = ([string]$Packaging.electronWin32X64Sha256).ToLowerInvariant()
$DeclaredElectron = [string]$PackageMetadata.dependencies.electron
if ([string]::IsNullOrWhiteSpace($ElectronVersion)) {
  throw "sentinelPackaging.electronVersion is required"
}
if ($DeclaredElectron -ne $ElectronVersion) {
  throw "Electron dependency must be pinned exactly to sentinelPackaging.electronVersion"
}
if ($ExpectedSha256 -notmatch '^[0-9a-f]{64}$') {
  throw "sentinelPackaging.electronWin32X64Sha256 must be a SHA-256 digest"
}

if ([string]::IsNullOrWhiteSpace($CacheDir)) {
  $CacheDir = Join-Path ([System.IO.Path]::GetTempPath()) "sentinel-electron-cache"
}
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$EvidenceDir = [System.IO.Path]::GetFullPath($EvidenceDir)
$CacheDir = [System.IO.Path]::GetFullPath($CacheDir)

New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
if (Test-Path $OutputDir) {
  Remove-Item -Recurse -Force $OutputDir
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$AssetName = "electron-v$ElectronVersion-win32-x64.zip"
$AssetUrl = "https://github.com/electron/electron/releases/download/v$ElectronVersion/$AssetName"
$ArchivePath = Join-Path $CacheDir $AssetName

if (-not (Test-Path $ArchivePath)) {
  Write-Host "Downloading pinned Electron runtime $AssetName"
  Invoke-WebRequest -Uri $AssetUrl -OutFile $ArchivePath
}

$ActualSha256 = (Get-FileHash -Algorithm SHA256 -Path $ArchivePath).Hash.ToLowerInvariant()
if ($ActualSha256 -ne $ExpectedSha256) {
  Remove-Item -Force $ArchivePath -ErrorAction SilentlyContinue
  throw "Electron runtime digest mismatch: expected $ExpectedSha256, got $ActualSha256"
}

Expand-Archive -LiteralPath $ArchivePath -DestinationPath $OutputDir -Force
$ElectronExe = Join-Path $OutputDir "electron.exe"
if (-not (Test-Path $ElectronExe)) {
  throw "Electron archive did not contain electron.exe"
}
$SentinelExe = Join-Path $OutputDir "SENTINEL Companion.exe"
Move-Item -LiteralPath $ElectronExe -Destination $SentinelExe

$DefaultApp = Join-Path $OutputDir "resources/default_app.asar"
if (Test-Path $DefaultApp) {
  Remove-Item -Force $DefaultApp
}

$AppDir = Join-Path $OutputDir "resources/app"
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
$ApplicationSources = @(
  "accessibility-runtime.js",
  "assets/sentinel-glyph.svg",
  "assets/sentinel-glyph-mono.svg",
  "assets/sentinel-icon-64.png",
  "assets/sentinel-master-512.png",
  "bootstrap.js",
  "companion-process.js",
  "companion-worker.js",
  "core-session.js",
  "exact-environment-evidence.js",
  "index.html",
  "main.js",
  "overlay-preload.js",
  "overlay-renderer.js",
  "overlay-state.js",
  "overlay.html",
  "package-smoke.js",
  "package.json",
  "packaged-runtime.js",
  "preload.js",
  "renderer.js",
  "runtime-health.js",
  "voice-runtime.js",
  "wow-savedvariables.js"
)
foreach ($RelativePath in $ApplicationSources) {
  $SourcePath = Join-Path $LauncherDir $RelativePath
  if (-not (Test-Path $SourcePath -PathType Leaf)) {
    throw "Required launcher source is missing: $RelativePath"
  }
  $DestinationPath = Join-Path $AppDir $RelativePath
  $DestinationParent = Split-Path -Parent $DestinationPath
  New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
  Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath
}

$SourceSha = if (-not [string]::IsNullOrWhiteSpace($env:SENTINEL_SOURCE_SHA)) {
  $env:SENTINEL_SOURCE_SHA
} elseif (-not [string]::IsNullOrWhiteSpace($env:GITHUB_SHA)) {
  $env:GITHUB_SHA
} else {
  "local-unbound"
}

$RuntimeProvenance = [ordered]@{
  schema = "sentinel.packaged-companion-runtime.v1"
  sourceSha = $SourceSha
  target = "win32-x64"
  packageVersion = [string]$PackageMetadata.version
  electronVersion = $ElectronVersion
  signed = $false
}
$RuntimeProvenancePath = Join-Path $AppDir "build-provenance.json"
[System.IO.File]::WriteAllText(
  $RuntimeProvenancePath,
  (($RuntimeProvenance | ConvertTo-Json -Depth 4) + "`n"),
  [System.Text.UTF8Encoding]::new($false)
)

if (Test-Path (Join-Path $AppDir "node_modules")) {
  throw "node_modules must not be packaged"
}
if (Test-Path (Join-Path $AppDir "test")) {
  throw "launcher tests must not be packaged"
}

$RootPrefixLength = $OutputDir.TrimEnd([char[]]@('\', '/')).Length + 1
$ManifestLines = Get-ChildItem -Path $OutputDir -File -Recurse |
  ForEach-Object {
    $RelativePath = $_.FullName.Substring($RootPrefixLength).Replace('\', '/')
    [PSCustomObject]@{
      RelativePath = $RelativePath
      Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
  } |
  Sort-Object RelativePath |
  ForEach-Object { "$($_.Hash)  $($_.RelativePath)" }

$ManifestPath = Join-Path $EvidenceDir "package-manifest.sha256"
[System.IO.File]::WriteAllLines(
  $ManifestPath,
  [string[]]$ManifestLines,
  [System.Text.UTF8Encoding]::new($false)
)

$Evidence = [ordered]@{
  schema = "sentinel.packaged-companion-build.v1"
  status = "pass"
  sourceSha = $SourceSha
  target = "win32-x64"
  packageVersion = [string]$PackageMetadata.version
  electronVersion = $ElectronVersion
  electronAsset = $AssetName
  electronAssetSha256 = $ActualSha256
  applicationPayload = "resources/app"
  applicationFileCount = $ApplicationSources.Count + 1
  embeddedRuntimeProvenance = "resources/app/build-provenance.json"
  packageManifest = "package-manifest.sha256"
  signed = $false
}
$EvidencePath = Join-Path $EvidenceDir "build-evidence.json"
[System.IO.File]::WriteAllText(
  $EvidencePath,
  (($Evidence | ConvertTo-Json -Depth 4) + "`n"),
  [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Packaged SENTINEL Companion $($PackageMetadata.version) using Electron $ElectronVersion"
Write-Host "Runtime SHA-256: $ActualSha256"
Write-Host "Embedded provenance: $RuntimeProvenancePath"
Write-Host "Canonical manifest: $ManifestPath"
