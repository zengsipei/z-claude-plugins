[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true)]
    [AllowEmptyString()]
    [string]$InputJson = ""
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Claude Code passes session_id, transcript_path, cwd, source, and model as JSON on stdin.
# pstack model configuration (written by /setup-pstack) is injected when present.
$raw = $InputJson
if ([string]::IsNullOrWhiteSpace($raw)) {
    $raw = [Console]::In.ReadToEnd()
}

$cwd = (Get-Location).Path

if (-not [string]::IsNullOrWhiteSpace($raw)) {
    try {
        $payload = $raw | ConvertFrom-Json
        if ($payload.cwd) { $cwd = [string]$payload.cwd }
    }
    catch {
        # Invalid hook input must not block session startup.
    }
}

$configPath = Join-Path $HOME ".claude/pstack-models.md"

if (-not (Test-Path -LiteralPath $configPath)) {
    # No configuration yet: /setup-pstack has not run. Stay silent.
    exit 0
}

# Read via .NET, not Get-Content: Get-Content -Raw decorates the returned
# string with ETS note properties (PSPath etc.), and ConvertTo-Json then
# serializes additionalContext as an object instead of a plain string.
$content = [System.IO.File]::ReadAllText($configPath)
if ([string]::IsNullOrWhiteSpace($content)) {
    exit 0
}

$response = @{
    hookSpecificOutput = @{
        hookEventName     = "SessionStart"
        additionalContext = $content
    }
}

[Console]::WriteLine(($response | ConvertTo-Json -Depth 4 -Compress))
