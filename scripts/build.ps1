param(
    [string]$Python = (Join-Path $env:LOCALAPPDATA 'Python\bin\python.exe')
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:TEMP = Join-Path $repo '.build-temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $repo '.build-cache'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $repo '.build-pyinstaller'
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:PIP_CACHE_DIR,$env:PYINSTALLER_CONFIG_DIR | Out-Null
Push-Location $repo
try {
$venv = Join-Path $repo '.build-venv'
& $Python -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
$venvPython = Join-Path $venv 'Scripts\python.exe'
& $venvPython -m pip install --disable-pip-version-check --no-cache-dir -r (Join-Path $repo 'scripts\requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'Pinned PyInstaller installation failed' }
& $venvPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Synthetic tests failed' }
& $venvPython -m PyInstaller --onefile --windowed --noupx --clean `
    --name SpectatorTooltipPatcher --distpath (Join-Path $repo 'dist') `
    --workpath (Join-Path $repo 'build') --specpath (Join-Path $repo 'build') `
    (Join-Path $repo 'launch.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
$exe = Join-Path $repo 'dist\SpectatorTooltipPatcher.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Executable missing after build' }
$zip = Join-Path $repo 'dist\SpectatorTooltipPatcher-windows.zip'
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip }
Compress-Archive -LiteralPath $exe,(Join-Path $repo 'README.md'),(Join-Path $repo 'LICENSE') -DestinationPath $zip
Get-FileHash -Algorithm SHA256 -LiteralPath $exe,$zip | Format-Table -AutoSize
} finally {
    Pop-Location
}
