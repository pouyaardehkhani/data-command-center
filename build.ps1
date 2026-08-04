Set-Location $PSScriptRoot
& ".\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean DataCommandCenter.spec
Write-Output "Build output: $PSScriptRoot\dist\Data Command Center\DataCommandCenter.exe"
