param(
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Get-GrokHome {
    if (-not [string]::IsNullOrWhiteSpace($env:GROK_HOME)) {
        return $env:GROK_HOME
    }

    return (Join-Path $HOME ".grok")
}

function New-GrokHookConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HookScript
    )

    $escapedHookScript = $HookScript.Replace('"', '\"')
    $command = 'powershell -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $escapedHookScript

    [ordered]@{
        description = "SDLC Grok SessionStart identity injection for software-dev-process"
        hooks       = [ordered]@{
            SessionStart = @(
                [ordered]@{
                    hooks = @(
                        [ordered]@{
                            type    = "command"
                            command = $command
                            timeout = 15
                        }
                    )
                }
            )
        }
    }
}

function Test-ConfigMatchesHook {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath,
        [Parameter(Mandatory = $true)]
        [string]$HookScript
    )

    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        return $false
    }

    try {
        $raw = Get-Content -LiteralPath $ConfigPath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return $false
        }
        $config = $raw | ConvertFrom-Json
    }
    catch {
        return $false
    }

    if ($null -eq $config.hooks -or $null -eq $config.hooks.SessionStart) {
        return $false
    }

    foreach ($entry in @($config.hooks.SessionStart)) {
        if ($null -eq $entry.hooks) {
            continue
        }
        foreach ($hook in @($entry.hooks)) {
            if ($null -ne $hook.command -and ([string]$hook.command).Contains($HookScript)) {
                return $true
            }
        }
    }

    return $false
}

$grokHome = Get-GrokHome
$skillRoot = Split-Path -Parent $PSScriptRoot
$sourceHookScript = Join-Path $skillRoot "scripts\hooks\grok_session_start.ps1"
$installedHooksDir = Join-Path $grokHome "hooks"
$installedHookScript = Join-Path $installedHooksDir "sdlc_grok_session_start.ps1"
$hooksJsonPath = Join-Path $installedHooksDir "sdlc-session-start.json"

if (-not (Test-Path -LiteralPath $sourceHookScript)) {
    throw "Hook script not found: $sourceHookScript"
}

if (-not (Test-Path -LiteralPath $grokHome)) {
    if ($DryRun) {
        Write-Host "[dry-run] Would create Grok home: $grokHome"
    }
    else {
        New-Item -ItemType Directory -Path $grokHome -Force | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $installedHooksDir)) {
    if ($DryRun) {
        Write-Host "[dry-run] Would create hooks directory: $installedHooksDir"
    }
    else {
        New-Item -ItemType Directory -Path $installedHooksDir -Force | Out-Null
    }
}

$configMatches = Test-ConfigMatchesHook -ConfigPath $hooksJsonPath -HookScript $installedHookScript
$configChanged = $true
if ($configMatches -and -not $Force) {
    $configChanged = $false
}

$config = New-GrokHookConfig -HookScript $installedHookScript
$json = $config | ConvertTo-Json -Depth 20

if ($DryRun) {
    Write-Host "[dry-run] Would refresh hook script: $sourceHookScript -> $installedHookScript"
    if ($configChanged) {
        Write-Host "[dry-run] Would update: $hooksJsonPath"
        Write-Host $json
    }
    else {
        Write-Host "[dry-run] sdlc-session-start.json already points at the expected hook script."
    }
    exit 0
}

Copy-Item -LiteralPath $sourceHookScript -Destination $installedHookScript -Force

if ($configChanged) {
    if (Test-Path -LiteralPath $hooksJsonPath) {
        $timestamp = Get-Date -Format "yyyyMMddHHmmss"
        $backupPath = "$hooksJsonPath.bak.$timestamp"
        Copy-Item -LiteralPath $hooksJsonPath -Destination $backupPath
        Write-Host "Backup written: $backupPath"
    }

    [System.IO.File]::WriteAllText($hooksJsonPath, $json, [System.Text.UTF8Encoding]::new($false))
}

Write-Host "SDLC Grok SessionStart hook installed."
Write-Host "hooks config: $hooksJsonPath"
Write-Host "source hook script: $sourceHookScript"
Write-Host "installed hook script: $installedHookScript"
if (-not $configChanged) {
    Write-Host "Existing hook config preserved; installed hook script was refreshed."
}
Write-Host "Restart Grok or start a new session to load the hook. Verify with /hooks."
