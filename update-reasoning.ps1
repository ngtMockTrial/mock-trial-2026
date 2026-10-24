$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$trialPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $trialPython)) { $trialPython = 'python' }
& $trialPython (Join-Path $PSScriptRoot '作成用/reasoning_graph.py')
$trialBuildExit = $LASTEXITCODE
if ($trialBuildExit -ne 0) { exit $trialBuildExit }
# 大量の派生ノート更新後もメタデータと描画を揃える。閉じているアプリは起動しない。
$trialCli = Join-Path $env:LOCALAPPDATA 'Programs/Obsidian/Obsidian.com'
if (-not (Test-Path -LiteralPath $trialCli)) {
    $trialCliCommand = Get-Command obsidian -ErrorAction SilentlyContinue
    if ($trialCliCommand) { $trialCli = $trialCliCommand.Source }
}
if ((Test-Path -LiteralPath $trialCli) -and (Get-Process Obsidian -ErrorAction SilentlyContinue)) {
    $trialVault = Split-Path -Leaf $PSScriptRoot
    & $trialCli "vault=$trialVault" reload
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
