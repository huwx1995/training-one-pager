param([Parameter(Mandatory=$true)][string]$BuildRoot)
$ErrorActionPreference = 'Stop'
$BuildRoot = (Resolve-Path $BuildRoot).Path
$Tools = Join-Path $BuildRoot 'tools'
New-Item -ItemType Directory -Force $Tools | Out-Null
$Whisper = Join-Path $BuildRoot 'upstream/whisper.cpp-1.7.6'
$WhisperBuild = Join-Path $BuildRoot 'whisper-build'
& cmake -S $Whisper -B $WhisperBuild -A x64 `
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded -DBUILD_SHARED_LIBS=OFF `
  -DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF `
  -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF `
  -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF -DWHISPER_CURL=OFF
if ($LASTEXITCODE -ne 0) { throw 'whisper configure failed' }
& cmake --build $WhisperBuild --config Release --target whisper-cli --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'whisper build failed' }
Copy-Item (Join-Path $WhisperBuild 'bin/Release/whisper-cli.exe') $Tools
$WhisperFastBuild = Join-Path $BuildRoot 'whisper-build-avx2'
& cmake -S $Whisper -B $WhisperFastBuild -A x64 `
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded -DBUILD_SHARED_LIBS=OFF `
  -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_AVX512=OFF `
  -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF `
  -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF -DWHISPER_CURL=OFF
if ($LASTEXITCODE -ne 0) { throw 'AVX2 whisper configure failed' }
& cmake --build $WhisperFastBuild --config Release --target whisper-cli --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'AVX2 whisper build failed' }
Copy-Item (Join-Path $WhisperFastBuild 'bin/Release/whisper-cli.exe') (Join-Path $Tools 'whisper-cli-avx2.exe')

# A full commit fixes the registry and its source archive hashes.
$VcpkgCommit = '6323816b53236bc9c8e10b1898456fb8e24725b9'
$Vcpkg = Join-Path $BuildRoot 'vcpkg'
if (!(Test-Path (Join-Path $Vcpkg '.git'))) {
  & git init $Vcpkg
  if ($LASTEXITCODE -ne 0) { throw 'vcpkg init failed' }
  & git -C $Vcpkg remote add origin https://github.com/microsoft/vcpkg.git
  if ($LASTEXITCODE -ne 0) { throw 'vcpkg remote failed' }
}
& git -C $Vcpkg fetch --depth 1 origin $VcpkgCommit
if ($LASTEXITCODE -ne 0) { throw 'vcpkg fetch failed' }
& git -C $Vcpkg checkout --detach $VcpkgCommit
if ($LASTEXITCODE -ne 0) { throw 'vcpkg checkout failed' }
& (Join-Path $Vcpkg 'bootstrap-vcpkg.bat') -disableMetrics
if ($LASTEXITCODE -ne 0) { throw 'vcpkg bootstrap failed' }
# Static libraries and CRT; customers do not install a compiler or runtime.
& (Join-Path $Vcpkg 'vcpkg.exe') install 'tesseract[core]:x64-windows-static' --disable-metrics
if ($LASTEXITCODE -ne 0) { throw 'Tesseract build failed' }
$Installed = Join-Path $Vcpkg 'installed/x64-windows-static'
Copy-Item (Join-Path $Installed 'tools/tesseract/tesseract.exe') $Tools
$Licenses = Join-Path $BuildRoot 'windows-licenses'
New-Item -ItemType Directory -Force $Licenses | Out-Null
# Preserve notices from all resolved dependencies, rather than guessing licenses.
Get-ChildItem (Join-Path $Installed 'share') -Directory | ForEach-Object {
  $Copyright = Join-Path $_.FullName 'copyright'
  if (Test-Path $Copyright) { Copy-Item $Copyright (Join-Path $Licenses ($_.Name + '-copyright.txt')) }
}
Copy-Item (Join-Path $BuildRoot 'tessdata/LICENSE') (Join-Path $Licenses 'tessdata-fast-LICENSE.txt')
Copy-Item (Join-Path $Vcpkg 'LICENSE.txt') (Join-Path $Licenses 'vcpkg-LICENSE.txt')
& (Join-Path $Vcpkg 'vcpkg.exe') list --disable-metrics | Out-File -Encoding utf8 (Join-Path $BuildRoot 'vcpkg-packages.txt')
if ($LASTEXITCODE -ne 0) { throw 'vcpkg package listing failed' }
