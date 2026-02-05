$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$OutRoot,
    [string]$OutZip = ""
)

function Require-Path($Path) {
    if (-not (Test-Path $Path)) {
        throw "Missing required path: $Path"
    }
}

function New-Manifest($Root, $OutPath) {
    $files = Get-ChildItem -Path $Root -Recurse -File
    $items = @()
    foreach ($f in $files) {
        $hash = Get-FileHash -Algorithm SHA256 -Path $f.FullName
        $items += [PSCustomObject]@{
            path = $f.FullName.Substring($Root.Length + 1) -replace "\\", "/"
            bytes = $f.Length
            sha256 = $hash.Hash
            mtime = $f.LastWriteTime.ToString("s")
        }
    }
    $items | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $OutPath
}

function Write-Readme($Path, $OutRootRel) {
    $content = @"
# 全跑复现包说明（中文）

本压缩包包含 2025 Task2 全跑复现产物（含 PSO-only / GA-only / Hybrid + Ablation + Analysis），以及论文与手册材料。

## 目录结构

- `data/processed/`：清洗数据与图对象（graph.pkl / *_clean.csv / 绘图资产）
- `outputs/$OutRootRel/`：本次 full-run 的全部产物
  - `task2/ablation_results.csv`：消融结果表（含多算法对比）
  - `task2/ablation_summary.md`：对比统计 + LaTeX 片段
  - `task2/viz/`：箱线图/收敛曲线/热图等
  - `task2/best_solution.json`：最终 Hybrid 解
- `paper/*.pdf`：论文 PDF（若已编译）
- `docs/new_problem_runbook.md`：运行手册
- `流程图/D题流程图-2026-01-18-updated.mmd`：流程图源文件

## 复现入口（手动）

```powershell
pwsh scripts/reproduce_2025_full_manual.ps1 -Full -SeedBase 42 -Repeats 5
```

## Task2 消融与对比产物位置

- `outputs/$OutRootRel/task2/ablation_results.csv`
- `outputs/$OutRootRel/task2/ablation_summary.md`
- `outputs/$OutRootRel/task2/viz/*.png`
"@
    $content | Set-Content -Encoding UTF8 $Path
}

if (-not (Test-Path $OutRoot)) {
    throw "OutRoot not found: $OutRoot"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $handoffDir = Join-Path $repoRoot "handoff"
    New-Item -ItemType Directory -Force -Path $handoffDir | Out-Null

    if (-not $OutZip -or $OutZip -eq "") {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $OutZip = Join-Path $handoffDir "fullrun_$timestamp.zip"
    }

    $readme = Join-Path $handoffDir "README_CN.md"
    $manifest = Join-Path $handoffDir "MANIFEST.json"

    $outRootRel = (Resolve-Path $OutRoot).Path.Substring($repoRoot.Length + 1) -replace "\\", "/"

    Write-Readme -Path $readme -OutRootRel $outRootRel

    $packRoot = Join-Path $handoffDir "_package_tmp"
    if (Test-Path $packRoot) { Remove-Item -Recurse -Force $packRoot }
    New-Item -ItemType Directory -Force -Path $packRoot | Out-Null

    # copy required contents
    Copy-Item -Recurse -Force "data/processed" (Join-Path $packRoot "data/processed")
    Copy-Item -Recurse -Force $OutRoot (Join-Path $packRoot $outRootRel)
    if (Test-Path "paper/main_submission.pdf") { Copy-Item -Force "paper/main_submission.pdf" (Join-Path $packRoot "paper/main_submission.pdf") }
    if (Test-Path "paper/ai_appendix.pdf") { Copy-Item -Force "paper/ai_appendix.pdf" (Join-Path $packRoot "paper/ai_appendix.pdf") }
    if (Test-Path "paper/main_submission_cn.tex") { Copy-Item -Force "paper/main_submission_cn.tex" (Join-Path $packRoot "paper/main_submission_cn.tex") }
    Copy-Item -Recurse -Force "docs" (Join-Path $packRoot "docs")
    if (Test-Path "流程图/D题流程图-2026-01-18-updated.mmd") { Copy-Item -Force "流程图/D题流程图-2026-01-18-updated.mmd" (Join-Path $packRoot "流程图/D题流程图-2026-01-18-updated.mmd") }
    if (Test-Path "plans") { Copy-Item -Recurse -Force "plans" (Join-Path $packRoot "plans") }

    # write README and manifest into pack
    Copy-Item -Force $readme (Join-Path $packRoot "README_CN.md")
    New-Manifest -Root $packRoot -OutPath $manifest
    Copy-Item -Force $manifest (Join-Path $packRoot "MANIFEST.json")

    if (Test-Path $OutZip) { Remove-Item -Force $OutZip }
    Compress-Archive -Path (Join-Path $packRoot "*") -DestinationPath $OutZip
    Remove-Item -Recurse -Force $packRoot

    Write-Host "OK: packaged fullrun to $OutZip"
    Write-Host "OK: manifest at $manifest"
} finally {
    Pop-Location
}
