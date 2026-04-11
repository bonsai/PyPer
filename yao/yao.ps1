# yao.ps1 — Windows entry point → WSL Python
param(
    [string]$Command = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

# Build safe argument string
$allArgs = @()
if ($Command) { $allArgs += $Command }
$allArgs += $ExtraArgs

# Escape each arg for wsl bash -c
$escaped = ($allArgs | ForEach-Object { "'" + ($_ -replace "'", "'\\''") + "'" }) -join " "

if (-not $escaped) { $escaped = "'help'" }

$wslCmd = "python3 ~/scripts/yao/yao.py $escaped"
wsl bash -c $wslCmd
