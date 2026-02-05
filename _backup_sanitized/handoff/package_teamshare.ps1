$ErrorActionPreference = "Stop"

Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    python handoff/pack_task_artifacts.py --out_dir handoff
    if ($LASTEXITCODE -ne 0) {
        throw "pack_task_artifacts.py failed with exit code $LASTEXITCODE"
    }
    Write-Host "OK: created handoff/task1_artifacts.zip"
    Write-Host "OK: created handoff/task2_artifacts.zip"
    Write-Host "OK: created handoff/task3_artifacts.zip"
    Write-Host "OK: created handoff/all_teamshare.zip"
} catch {
    Write-Error $_.Exception.Message
    exit 1
} finally {
    Pop-Location
}
