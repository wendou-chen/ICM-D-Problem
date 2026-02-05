import re
import os
import argparse
import sys
from datetime import datetime

def markdown_to_latex(md_content, image_base_dir="."):
    """
    A lightweight, robust parser to convert specific Markdown structures to LaTeX.
    Focuses on: Headers, Lists, Tables, and Images.
    """
    lines = md_content.split('\n')
    tex_lines = []

    # LaTeX Preamble
    tex_lines.append(r"\documentclass{article}")
    tex_lines.append(r"\usepackage{graphicx}")  # For images
    tex_lines.append(r"\usepackage{hyperref}")  # For links
    tex_lines.append(r"\usepackage{booktabs}")  # For tables
    tex_lines.append(r"\usepackage{longtable}") # For long tables
    tex_lines.append(r"\usepackage[utf8]{inputenc}") # UTF-8 support
    tex_lines.append(r"\usepackage{xeCJK}") # Chinese support (critical for this agent)
    tex_lines.append(r"\setCJKmainfont{SimSun}") # Use system font, fallback might be needed
    tex_lines.append(r"\usepackage{geometry}")
    tex_lines.append(r"\geometry{a4paper, margin=1in}")
    tex_lines.append(r"\title{Modeling Interpretation Brief}")
    tex_lines.append(r"\author{Model Interpreter Agent}")
    tex_lines.append(r"\date{\today}")
    tex_lines.append(r"\begin{document}")
    tex_lines.append(r"\maketitle")

    in_table = False
    table_header = []
    table_rows = []

    for line in lines:
        line = line.strip()

        # 1. Skip Empty lines (unless needing paragraph break)
        if not line:
            if in_table:
                # Flush table
                tex_lines.append(generate_latex_table(table_header, table_rows))
                in_table = False
                table_header = []
                table_rows = []
            tex_lines.append(r"\par")
            continue

        # 2. Headers
        if line.startswith('#'):
            level = len(line.split()[0])
            text = line.lstrip('#').strip()
            if level == 1: tex_lines.append(f"\\section*{{{text}}}")
            elif level == 2: tex_lines.append(f"\\subsection*{{{text}}}")
            elif level == 3: tex_lines.append(f"\\subsubsection*{{{text}}}")
            continue

        # 3. Images: ![Caption](Path)
        img_match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if img_match:
            caption = img_match.group(1)
            path = img_match.group(2)
            # Fix path for windows/latex compatibility
            path = path.replace('\\', '/')

            tex_lines.append(r"\begin{figure}[h!]")
            tex_lines.append(r"\centering")
            # Limit image width
            tex_lines.append(f"\\includegraphics[width=0.8\\textwidth]{{{path}}}")
            tex_lines.append(f"\\caption{{{caption}}}")
            tex_lines.append(r"\end{figure}")
            continue

        # 4. Tables
        if line.startswith('|'):
            if '---' in line: continue # Skip separator
            row = [c.strip() for c in line.strip('|').split('|')]
            # Escape special chars in table cells, unless they look like math
            safe_row = []
            for cell in row:
                if '$' in cell:
                    safe_row.append(cell) # Assume math is handled by user or basic parser
                else:
                    safe_row.append(cell.replace('_', r'\_').replace('%', r'\%'))

            if not in_table:
                in_table = True
                table_header = safe_row
            else:
                table_rows.append(safe_row)
            continue

        # 5. Math (Basic)
        # Convert $$...$$ to \[...\]
        if line.startswith('$$') and line.endswith('$$'):
            math_content = line.strip('$')
            tex_lines.append(f"\\[ {math_content} \\]")
            continue

        # 6. Normal Text (escape special chars?)
        # For simplicity, we assume the agent writes relatively clean text.
        # Minimal escaping:
        safe_line = line.replace('%', '\\%').replace('_', '\\_')
        tex_lines.append(safe_line)

    # Final flush
    if in_table:
         tex_lines.append(generate_latex_table(table_header, table_rows))

    tex_lines.append(r"\end{document}")
    return "\n".join(tex_lines)

def generate_latex_table(header, rows):
    cols = len(header)
    col_def = "l" * cols # Left align all
    tex = []
    tex.append(r"\begin{center}")
    tex.append(f"\\begin{{longtable}}{{{col_def}}}")
    tex.append(r"\toprule")
    tex.append(" & ".join(header) + r" \\")
    tex.append(r"\midrule")
    for row in rows:
        # Pad row if missing cols
        if len(row) < cols: row += [""] * (cols - len(row))
        tex.append(" & ".join(row[:cols]) + r" \\")
    tex.append(r"\bottomrule")
    tex.append(r"\end{longtable}")
    tex.append(r"\end{center}")
    return "\n".join(tex)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Markdown Brief to LaTeX")
    parser.add_argument("--input", required=True, help="Input markdown file")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tex_content = markdown_to_latex(content)

    output_tex = input_path.replace('.md', '.tex')
    with open(output_tex, 'w', encoding='utf-8') as f:
        f.write(tex_content)

    print(f"[SUCCESS] Successfully generated LaTeX source: {output_tex}")

    # Auto-compile to PDF if on Windows (simplification for this environment)
    import subprocess
    import os

    # Determine output directory from the input tex file path
    output_dir = os.path.dirname(output_tex)
    if not output_dir:
        output_dir = "."

    print(f"[INFO] Compiling PDF to {output_dir}...")

    try:
        # Use -output-directory to ensure PDF lands next to the tex file
        # Use -interaction=nonstopmode to prevent hanging on errors
        cmd = f'xelatex -output-directory="{output_dir}" -interaction=nonstopmode "{output_tex}"'
        subprocess.run(cmd, shell=True, check=True)

        pdf_path = output_tex.replace('.tex', '.pdf')
        print(f"[SUCCESS] PDF generated: {pdf_path}")

        # Cleanup auxiliary files
        print("[INFO] Cleaning up auxiliary files...")
        base_path = output_tex.replace('.tex', '')
        for ext in ['.aux', '.log', '.out']:
            junk_file = base_path + ext
            if os.path.exists(junk_file):
                os.remove(junk_file)

    except subprocess.CalledProcessError:
        print("[ERROR] PDF compilation failed. Please check the .log file.")
        # Don't delete logs if failed, user might need them

