$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    $latexmk = Get-Command latexmk -ErrorAction SilentlyContinue
    $pdflatex = Get-Command pdflatex -ErrorAction SilentlyContinue
    $bibtex = Get-Command bibtex -ErrorAction SilentlyContinue

    if ($latexmk) {
        latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
    } elseif ($pdflatex) {
        pdflatex main.tex
        if ($bibtex) {
            bibtex main
        }
        pdflatex main.tex
        pdflatex main.tex
    } else {
        throw "LaTeX not found. Install latexmk or pdflatex."
    }

    if (-not (Test-Path "main.pdf")) {
        throw "main.pdf not generated."
    }
    $info = Get-Item "main.pdf"
    if ($info.Length -le 0) {
        throw "main.pdf is empty."
    }
    Write-Host "Build succeeded: $($info.FullName)"
} catch {
    Write-Error $_.Exception.Message
    exit 1
} finally {
    Pop-Location
}
