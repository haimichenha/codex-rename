param(
    [Parameter(Position = 0, Mandatory = $true)]
    [string]$Provider,

    [Parameter(Position = 1)]
    [string]$Thread = "",

    [switch]$NoSyncCurrent,
    [switch]$DryRun,
    [switch]$NoDiag,

    [string]$BaseUrl = "",
    [string]$ApiKey = "",
    [string]$ApiKeyEnv = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$helper = Join-Path $scriptDir "codex_switch_manager.py"

$argsList = @($helper, "switch", $Provider)

if ($Thread -ne "") {
    $argsList += @("--thread", $Thread)
}

if ($NoSyncCurrent) {
    $argsList += "--no-sync-current"
}

if ($BaseUrl -ne "") {
    $argsList += @("--base-url", $BaseUrl)
}

if ($ApiKey -ne "") {
    $argsList += @("--api-key", $ApiKey)
}

if ($ApiKeyEnv -ne "") {
    $argsList += @("--api-key-env", $ApiKeyEnv)
}

if (-not $DryRun) {
    $argsList += "--write"
}

$switchOutput = python @argsList
$exitCode = $LASTEXITCODE
$switchOutput

if ($exitCode -ne 0) {
    exit $exitCode
}

if (-not $DryRun -and -not $NoDiag) {
    Write-Host ""
    Write-Host "Current Codex provider diagnostics:"
    python $helper "diag"
    exit $LASTEXITCODE
}

exit $exitCode

