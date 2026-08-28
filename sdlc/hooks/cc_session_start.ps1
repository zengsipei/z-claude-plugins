[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true)]
    [AllowEmptyString()]
    [string]$InputJson = ""
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Claude Code passes session_id, transcript_path, cwd, source, and model as JSON on stdin.
$raw = $InputJson
if ([string]::IsNullOrWhiteSpace($raw)) {
    $raw = [Console]::In.ReadToEnd()
}

$sessionId = ""
$cwd = (Get-Location).Path
$model = ""
$source = ""

if (-not [string]::IsNullOrWhiteSpace($raw)) {
    try {
        $payload = $raw | ConvertFrom-Json
        if ($payload.session_id) { $sessionId = [string]$payload.session_id }
        if ($payload.cwd) { $cwd = [string]$payload.cwd }
        if ($payload.model) { $model = [string]$payload.model }
        if ($payload.source) { $source = [string]$payload.source }
    }
    catch {
        # Invalid hook input must not block session startup.
    }
}

$contextLines = @(
    "SDLC Claude Code SessionStart hook is active.",
    "When using sdlc, maintain AI registration via scripts/ai_register_core.py (PostgreSQL/MySQL config first, project SQLite fallback). Never guess a missing session id from transcript timestamps.",
    "Current working directory: $cwd"
)

if (-not [string]::IsNullOrWhiteSpace($sessionId)) {
    $contextLines += "Current Claude Code session id: $sessionId"
}
else {
    $contextLines += "Current Claude Code session id is unavailable; skip AI registration rather than guessing."
}

if (-not [string]::IsNullOrWhiteSpace($model)) {
    $contextLines += "Current model: $model"
}

if (-not [string]::IsNullOrWhiteSpace($source)) {
    $contextLines += "Session source: $source"
}

$response = @{
    hookSpecificOutput = @{
        hookEventName     = "SessionStart"
        additionalContext = ($contextLines -join "`n")
    }
}

[Console]::WriteLine(($response | ConvertTo-Json -Depth 4 -Compress))
