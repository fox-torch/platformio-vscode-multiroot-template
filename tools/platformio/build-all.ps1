[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$toolsRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $toolsRoot
. (Join-Path $PSScriptRoot 'project-discovery.ps1')
. (Join-Path $PSScriptRoot 'platformio-common.ps1')
$pio = Get-PlatformIOExecutable

$projects = @(Get-PlatformIOProjects -RepositoryRoot $repoRoot)
if ($projects.Count -eq 0) {
    Write-Host 'No PlatformIO projects found.'
    exit 0
}

$failed = @()
foreach ($project in $projects) {
    Write-Host "`n=== Build: $($project.Id) ==="
    & $pio run --project-dir $project.Directory
    if ($LASTEXITCODE -ne 0) {
        $failed += $project.Id
    }
}
if ($failed.Count -gt 0) {
    Write-Host "`nBuild failed:" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "- $_" -ForegroundColor Red }
    exit 1
}

Write-Host "`nAll PlatformIO projects built successfully."
