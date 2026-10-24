$ErrorActionPreference = 'Stop'
$taskNote = Join-Path $PSScriptRoot '検討/00_はじめに.md'
Start-Process ('obsidian://open?path=' + [Uri]::EscapeDataString($taskNote))
