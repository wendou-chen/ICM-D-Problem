import os
import re
import subprocess
import argparse

def parse_markdown_to_tex(md_content):
    """
    将特定的 Markdown 内容转换为 LaTeX 源码。
    专门优化了中文支持和图片插入功能。
    """
    lines = md_content.split('\n')
    tex_lines = []
    
    # LaTeX Preamble (针对中文优化)
    tex_lines.append(r"\documentclass[a4paper,12pt]{article}")
    tex_lines.append(r"\usepackage[UTF8]{ctex}")  # 关键：中文支持
    tex_lines.append(r"\usepackage{graphicx}")    # 图片支持
    tex_lines.append(r"\usepackage{amsmath}")     # 数学公式
    tex_lines.append(r"\usepackage{geometry}")
    tex_lines.append(r"\usepackage{hyperref}")
    tex_lines.append(r"\usepackage{booktabs}")    # 表格美化
    tex_lines.append(r"\usepackage{longtable}")   # 长表格
    tex_lines.append(r"\geometry{left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm}")
    tex_lines.append(r"\title{MCM-B 建模内参 (Modeling Brief)}")
    tex_lines.append(r"\author{Model_Interpreter_CN}")
    tex_lines.append(r"\date{\today}")
    tex_lines.append(r"\begin{document}")
    tex_lines.append(r"\maketitle")
    tex_lines.append(r"\tableofcontents")
    tex_lines.append(r"\newpage")

    in_table = False
    table_aligns = []
    
    for line in lines:
        line = line.strip()
        
        # 1. Headers
        if line.startswith('# '):
            tex_lines.append(f"\\section{{{line[2:]}}}")
        elif line.startswith('## '):
            tex_lines.append(f"\\subsection{{{line[3:]}}}")
        elif line.startswith('### '):
            tex_lines.append(f"\\subsubsection{{{line[4:]}}}")
            
        # 2. Images: ![Caption](Path)
        elif re.match(r'!\[(.*?)\]\((.*?)\)', line):
            match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
            caption = match.group(1)
            path = match.group(2)
            # 转换为 LaTeX figure 环境
            tex_lines.append(r"\begin{figure}[h!]")
            tex_lines.append(r"\centering")
            # 检查路径是否存在，避免编译报错
            if os.path.exists(path):
                tex_lines.append(f"\\includegraphics[width=0.9\\textwidth]{{{path}}}")
            else:
                tex_lines.append(f"\\textbf{{[Image Missing: {path}]}}")
            tex_lines.append(f"\\caption{{{caption}}}")
            tex_lines.append(r"\end{figure}")
            
        # 3. Simple Tables (Markdown 转换逻辑简化版)
        elif line.startswith('|'):
            if not in_table:
                tex_lines.append(r"\begin{center}")
                tex_lines.append(r"\begin{longtable}{|l|l|l|l|l|}") # 简化处理，默认5列
                tex_lines.append(r"\hline")
                in_table = True
            
            # 处理表格行，替换 | 为 &
            content = line.strip('|').split('|')
            row = " & ".join([c.strip() for c in content]) + r" \\ \hline"
            # 忽略分隔行 |---|
            if '---' in line:
                continue
            tex_lines.append(row)
            
        # 4. Math Blocks ($$ ... $$)
        elif line.startswith('$$') and line.endswith('$$'):
            math_content = line.strip('$')
            tex_lines.append(r"\begin{equation}")
            tex_lines.append(math_content)
            tex_lines.append(r"\end{equation}")

        # 5. Bullet Points
        elif line.startswith('* ') or line.startswith('- '):
            tex_lines.append(r"\begin{itemize}")
            tex_lines.append(f"\\item {line[2:]}")
            tex_lines.append(r"\end{itemize}") # 简化处理，每行一个列表环境(不够优雅但能用)
            # 更好的做法是维护列表状态，这里为保持脚本轻量做简化

        # 6. Normal Text
        else:
            if in_table and not line.startswith('|'):
                tex_lines.append(r"\end{longtable}")
                tex_lines.append(r"\end{center}")
                in_table = False
            
            if line:
                # 简单转义 LaTeX 特殊字符
                safe_line = line.replace('%', '\\%').replace('_', '\\_')
                tex_lines.append(f"{safe_line}\n")
                tex_lines.append(r"\par") # 段落换行

    tex_lines.append(r"\end{document}")
    return "\n".join(tex_lines)

def convert_md_to_pdf(input_md, output_filename="Modeling_Brief"):
    # 清理输出文件名：如果包含扩展名则移除
    if output_filename.lower().endswith('.pdf'):
        output_filename = output_filename[:-4]
    if output_filename.lower().endswith('.tex'):
        output_filename = output_filename[:-4]
    # 1. 读取 Markdown
    with open(input_md, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. 转换为 TeX 内容
    tex_content = parse_markdown_to_tex(content)
    
    tex_file = f"{output_filename}.tex"
    
    # 3. 写入 .tex 文件
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(tex_content)
    print(f"[Success] Generated LaTeX source: {tex_file}")
    
    # 4. 编译 PDF (调用 xelatex)
    try:
        # 运行两次以生成目录和引用
        subprocess.run(['xelatex', '-interaction=nonstopmode', tex_file], check=True)
        subprocess.run(['xelatex', '-interaction=nonstopmode', tex_file], check=True)
        print(f"[Success] Compiled PDF: {output_filename}.pdf")
    except FileNotFoundError:
        print("[Error] 'xelatex' command not found. Please install TeX Live or MiKTeX.")
    except subprocess.CalledProcessError:
        print("[Error] Compilation failed. Check the .log file.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Modeling Markdown to PDF with Images")
    parser.add_argument("input", help="Input markdown file path")
    parser.add_argument("--output", "-o", help="Output PDF filename (without extension)", default="Modeling_Brief")
    args = parser.parse_args()

    convert_md_to_pdf(args.input, args.output)