param(
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Get-CodexHome {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        return $env:CODEX_HOME
    }

    return (Join-Path $HOME ".codex")
}

function New-HookEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HookScript
    )

    $escapedHookScript = $HookScript.Replace("'", "''")
    $command = 'powershell -NoProfile -ExecutionPolicy Bypass -Command "[Console]::In.ReadToEnd() | & ''{0}''"' -f $escapedHookScript

    [ordered]@{
        matcher = "startup|resume|clear|compact"
        hooks   = @(
            [ordered]@{
                type          = "command"
                command       = $command
                timeout       = 10
                statusMessage = "Loading SDLC SessionStart context"
            }
        )
    }
}

function ConvertTo-Hashtable {
    param(
        [Parameter(Mandatory = $true)]
        $Value
    )

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string] -and $Value -isnot [System.Collections.IDictionary]) {
        $items = @()
        foreach ($item in $Value) {
            $items += ConvertTo-Hashtable $item
        }
        return ,$items
    }

    if ($Value -is [pscustomobject]) {
        $table = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            $table[$property.Name] = ConvertTo-Hashtable $property.Value
        }
        return $table
    }

    return $Value
}

function Test-EntryMatchesHook {
    param(
        $Entry,
        [Parameter(Mandatory = $true)]
        [string]$HookScript
    )

    if ($null -eq $Entry.hooks) {
        return $false
    }

    foreach ($hook in @($Entry.hooks)) {
        if ($null -ne $hook.command -and $hook.command -like "*$HookScript*") {
            return $true
        }
    }

    return $false
}

function Test-EntryIsSdlcHook {
    param(
        $Entry
    )

    if ($null -eq $Entry.hooks) {
        return $false
    }

    foreach ($hook in @($Entry.hooks)) {
        if ($hook.statusMessage -eq "Loading SDLC SessionStart context") {
            return $true
        }

        if ($null -ne $hook.command) {
            $command = [string]$hook.command
            if ($command.Contains("sdlc_codex_session_start.ps1") -or $command.Contains("codex_session_start.ps1")) {
                return $true
            }
        }
    }

    return $false
}

$codexHome = Get-CodexHome
$skillRoot = Split-Path -Parent $PSScriptRoot
$sourceHookScript = Join-Path $skillRoot "scripts\hooks\codex_session_start.ps1"
$installedHooksDir = Join-Path $codexHome "hooks"
$installedHookScript = Join-Path $installedHooksDir "sdlc_codex_session_start.ps1"
$hooksJsonPath = Join-Path $codexHome "hooks.json"

if (-not (Test-Path -LiteralPath $sourceHookScript)) {
    throw "Hook script not found: $sourceHookScript"
}

if (-not (Test-Path -LiteralPath $codexHome)) {
    if ($DryRun) {
        Write-Host "[dry-run] Would create Codex home: $codexHome"
    }
    else {
        New-Item -ItemType Directory -Path $codexHome -Force | Out-Null
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

if (Test-Path -LiteralPath $hooksJsonPath) {
    $raw = Get-Content -LiteralPath $hooksJsonPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        $config = [ordered]@{ hooks = [ordered]@{} }
    }
    else {
        $config = ConvertTo-Hashtable ($raw | ConvertFrom-Json)
    }
}
else {
    $config = [ordered]@{ hooks = [ordered]@{} }
}

if ($null -eq $config.hooks) {
    $config.hooks = [ordered]@{}
}

if ($null -eq $config.hooks.SessionStart) {
    $config.hooks.SessionStart = @()
}

$existingEntries = @($config.hooks.SessionStart)
$hasEntry = $false
$hasLegacySdlcEntry = $false
foreach ($entry in $existingEntries) {
    if (Test-EntryMatchesHook -Entry $entry -HookScript $installedHookScript) {
        $hasEntry = $true
    }
    elseif (Test-EntryIsSdlcHook -Entry $entry) {
        $hasLegacySdlcEntry = $true
    }
}

$configChanged = $true

if ($hasEntry -and -not $Force -and -not $hasLegacySdlcEntry) {
    # Keep the valid config entry, but refresh the installed script after skill upgrades.
    $configChanged = $false
}
else {
    $keptEntries = @()
    foreach ($entry in $existingEntries) {
        if (-not (Test-EntryIsSdlcHook -Entry $entry)) {
            $keptEntries += $entry
        }
    }
    $config.hooks.SessionStart = $keptEntries

    $newEntry = New-HookEntry -HookScript $installedHookScript
    $config.hooks.SessionStart = @($config.hooks.SessionStart) + @($newEntry)
}

$json = $config | ConvertTo-Json -Depth 20

if ($DryRun) {
    Write-Host "[dry-run] Would refresh hook script: $sourceHookScript -> $installedHookScript"
    if ($configChanged) {
        Write-Host "[dry-run] Would update: $hooksJsonPath"
        Write-Host $json
    }
    else {
        Write-Host "[dry-run] hooks.json already contains the expected SessionStart entry."
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

Write-Host "SDLC Codex SessionStart hook installed."
Write-Host "hooks.json: $hooksJsonPath"
Write-Host "source hook script: $sourceHookScript"
Write-Host "installed hook script: $installedHookScript"
if (-not $configChanged) {
    Write-Host "Existing hooks.json entry preserved; installed hook script was refreshed."
}
Write-Host "Restart Codex or start a new session to load the hook."
