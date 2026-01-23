$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    $latexmk = Get-Command latexmk -ErrorAction SilentlyContinue
    $pdflatex = Get-Command pdflatex -ErrorAction SilentlyContinue
    $bibtex = Get-Command bibtex -ErrorAction SilentlyContinue

    function Build-TexFile($texFile) {
        if ($latexmk) {
            latexmk -pdf -interaction=nonstopmode -halt-on-error $texFile
        } elseif ($pdflatex) {
            pdflatex $texFile
            if ($bibtex) {
                $base = [System.IO.Path]::GetFileNameWithoutExtension($texFile)
                bibtex $base
            }
            pdflatex $texFile
            pdflatex $texFile
        } else {
            throw "LaTeX not found. Install latexmk or pdflatex."
        }
    }

    Build-TexFile "main_submission.tex"
    if (-not (Test-Path "main_submission.pdf")) {
        throw "main_submission.pdf not generated."
    }
    $mainInfo = Get-Item "main_submission.pdf"
    if ($mainInfo.Length -le 0) {
        throw "main_submission.pdf is empty."
    }

    Build-TexFile "ai_appendix.tex"
    if (-not (Test-Path "ai_appendix.pdf")) {
        throw "ai_appendix.pdf not generated."
    }
    $aiInfo = Get-Item "ai_appendix.pdf"
    if ($aiInfo.Length -le 0) {
        throw "ai_appendix.pdf is empty."
    }

    Write-Host "Build succeeded: $($mainInfo.FullName)"
    Write-Host "Build succeeded: $($aiInfo.FullName)"
} catch {
    Write-Error $_.Exception.Message
    exit 1
} finally {
    Pop-Location
}
