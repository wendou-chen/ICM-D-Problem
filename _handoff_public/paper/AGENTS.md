# 论文生成系统文档 (AGENTS.md)

## 1. 概览 (OVERVIEW)
本项目是一个自动化的 LaTeX 论文生成系统，支持从脚本自动生成数据表和可视化图表，并将其无缝集成到最终 PDF 中。

## 2. 目录结构 (STRUCTURE)
- **main.tex**: 论文主入口文件，通过 `\input` 命令组合各模块。
- **sections/**: 存放论文的各个章节（如 `methods.tex`, `results.tex` 等）。
- **tables/**: 存放自动生成的 LaTeX 表格文件。
- **snippets/**: 存放可复用的文本或数学符号片段（如 `notation.tex`）。

## 3. 构建指南 (BUILD)
在 PowerShell 环境下运行以下脚本进行编译：
```powershell
./paper/build.ps1
```
**构建逻辑**：
- 自动检测环境：优先使用 `latexmk`，若缺失则退而使用 `pdflatex`。
- 自动处理引用：包含 `bibtex` 编译流程。
- 生成产物：编译成功后将在 `paper/` 目录下生成 `main.pdf`。

## 4. 资源与资产 (ASSETS)
- **禁止手动修改表格**: 请勿直接编辑 `tables/` 目录下的 `.tex` 文件，否则会被覆盖。
- **自动化逻辑**: 
  - **表格**: 修改 `scripts/make_tables.py` 脚本来调整表格数据或格式。
  - **图表**: 修改 `scripts/viz_*.py` 脚本来调整可视化产物。
- **一致性**: 确保 `main.tex` 中的 `\input` 路径与物理文件结构保持一致。

---
*保持简洁，以脚本为准。*
