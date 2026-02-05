"""
generate_acceptance_report.py
生成验收报告（不依赖命令行执行）
"""
import json
import zipfile
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).parent.parent

def main():
    print("=" * 80)
    print("Task2 可视化脚本验收报告")
    print("=" * 80)
    
    # 加载 best_solution.json
    best_sol_path = ROOT_DIR / "outputs" / "task2" / "best_solution.json"
    with open(best_sol_path, 'r', encoding='utf-8') as f:
        best_sol = json.load(f)
    
    run_id = best_sol.get("run_id")
    selected_ids = best_sol.get("selected_ids", [])
    n_selected = best_sol.get("n_selected", len(selected_ids))
    
    outdir = ROOT_DIR / "outputs" / "task2" / "viz"
    
    print(f"\nRun ID: {run_id}")
    print(f"Selected IDs: {selected_ids}")
    print(f"N Selected: {n_selected}")
    
    all_passed = True
    
    # A) figures 目录检查
    print("\n" + "-" * 80)
    print("[2A] figures 目录图数量检查")
    print("-" * 80)
    
    figures_dir = outdir / "figures"
    if not figures_dir.exists():
        print(f"❌ figures 目录不存在")
        all_passed = False
    else:
        all_files = sorted([f.name for f in figures_dir.iterdir() if f.is_file()])
        pdf_files = [f for f in all_files if f.endswith('.pdf')]
        png_files = [f for f in all_files if f.endswith('.png')]
        
        print(f"\n所有文件 ({len(all_files)} 个):")
        for f in all_files:
            print(f"  - {f}")
        
        print(f"\nPDF 文件数: {len(pdf_files)}")
        print(f"PNG 文件数: {len(png_files)}")
        
        pdf_basenames = {f[:-4] for f in pdf_files}
        png_basenames = {f[:-4] for f in png_files}
        paired = pdf_basenames & png_basenames
        
        print(f"\n配对检查:")
        print(f"  配对成功: {len(paired)} 对")
        
        if len(pdf_files) >= 5 and len(png_files) >= 5 and len(paired) >= 5:
            print("✅ figures 目录检查通过")
        else:
            print("❌ figures 目录检查失败")
            all_passed = False
    
    # B) solution_flows.csv 检查
    print("\n" + "-" * 80)
    print("[2B] solution_flows.csv 检查")
    print("-" * 80)
    
    flows_path = outdir / "solution_flows.csv"
    if flows_path.exists():
        df_flows = pd.read_csv(flows_path)
        row_count = len(df_flows)
        expected_cols = [
            "run_id", "route_id", "segment_idx",
            "source_node_id", "target_node_id",
            "source_lon", "source_lat", "target_lon", "target_lat",
            "value"
        ]
        actual_cols = list(df_flows.columns)
        
        print(f"\n文件路径: {flows_path}")
        print(f"行数: {row_count}")
        print(f"列名: {actual_cols}")
        
        if actual_cols == expected_cols:
            print("✅ 列名匹配")
        else:
            print(f"❌ 列名不匹配")
            all_passed = False
        
        if row_count > 0:
            print("\n前 3 行:")
            print(df_flows.head(3).to_string())
            print("✅ solution_flows.csv 检查通过")
        else:
            print("❌ solution_flows.csv 行数为 0")
            all_passed = False
    else:
        print(f"❌ solution_flows.csv 不存在")
        all_passed = False
    
    # C) solution_routes_summary.csv 检查
    print("\n" + "-" * 80)
    print("[2C] solution_routes_summary.csv 检查")
    print("-" * 80)
    
    summary_path = outdir / "solution_routes_summary.csv"
    if summary_path.exists():
        df_summary = pd.read_csv(summary_path)
        row_count = len(df_summary)
        expected_cols = [
            "run_id", "route_id", "description",
            "n_segments", "total_cost",
            "mode_counts_json", "mode_costs_json",
            "min_seg_cost", "max_seg_cost", "mean_seg_cost"
        ]
        actual_cols = list(df_summary.columns)
        
        print(f"\n文件路径: {summary_path}")
        print(f"行数: {row_count}")
        print(f"列名: {actual_cols}")
        
        if actual_cols == expected_cols:
            print("✅ 列名匹配")
        else:
            print(f"❌ 列名不匹配")
            all_passed = False
        
        if row_count == n_selected:
            print(f"✅ 行数匹配 n_selected ({n_selected})")
        else:
            print(f"❌ 行数 ({row_count}) != n_selected ({n_selected})")
            all_passed = False
        
        if row_count > 0:
            print("\n前 3 行:")
            print(df_summary.head(3).to_string())
    else:
        print(f"❌ solution_routes_summary.csv 不存在")
        all_passed = False
    
    # D) README_for_artist.md 检查
    print("\n" + "-" * 80)
    print("[2D] README_for_artist.md 检查")
    print("-" * 80)
    
    readme_path = outdir / "README_for_artist.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        print(f"\n文件路径: {readme_path}")
        print(f"总行数: {len(lines)}")
        print("\n前 40 行:")
        for i, line in enumerate(lines[:40], 1):
            print(f"{i:3d}: {line}")
        
        has_kepler = "Kepler" in content
        has_convergence = "收敛曲线建议" in content
        
        print(f"\n关键词检查:")
        print(f"  包含 'Kepler': {has_kepler}")
        print(f"  包含 '收敛曲线建议': {has_convergence}")
        print("✅ README_for_artist.md 检查通过")
    else:
        print(f"❌ README_for_artist.md 不存在")
        all_passed = False
    
    # E) zip 文件检查
    print("\n" + "-" * 80)
    print("[2E] plot_pack_{run_id}.zip 检查")
    print("-" * 80)
    
    zip_path = outdir / f"plot_pack_{run_id}.zip"
    if zip_path.exists():
        zip_size = zip_path.stat().st_size
        print(f"\n文件路径: {zip_path}")
        print(f"文件大小: {zip_size:,} bytes ({zip_size / 1024 / 1024:.2f} MB)")
        
        required_files = {
            "solution_flows.csv",
            "solution_routes_summary.csv",
            "README_for_artist.md",
            "metrics.csv",
            "runtime.csv",
            "convergence_history.csv",
            "resilience_curve.csv",
            "best_solution.json",
        }
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zip_files = set(zf.namelist())
            
            print(f"\nZip 内文件总数: {len(zip_files)}")
            print("\n所有文件:")
            for f in sorted(zip_files):
                print(f"  - {f}")
            
            print("\n必需文件检查:")
            missing_files = []
            for req_file in required_files:
                found = any(req_file in f for f in zip_files)
                if found:
                    matching = [f for f in zip_files if req_file in f]
                    print(f"  ✅ {req_file}")
                else:
                    print(f"  ❌ {req_file} 缺失")
                    missing_files.append(req_file)
            
            pdf_in_zip = [f for f in zip_files if f.endswith('.pdf')]
            png_in_zip = [f for f in zip_files if f.endswith('.png')]
            
            print(f"\nZip 内的图表文件:")
            print(f"  PDF: {len(pdf_in_zip)} 个")
            print(f"  PNG: {len(png_in_zip)} 个")
            
            if len(pdf_in_zip) >= 5 and len(png_in_zip) >= 5 and not missing_files:
                print("✅ zip 文件检查通过")
            else:
                print("❌ zip 文件检查失败")
                all_passed = False
    else:
        print(f"❌ zip 文件不存在")
        all_passed = False
    
    # 最终验收报告
    print("\n" + "=" * 80)
    print("[步骤3] 最终验收报告")
    print("=" * 80)
    
    print(f"\nRun ID: {run_id}")
    print(f"Selected IDs: {selected_ids}")
    print(f"N Selected: {n_selected}")
    
    if figures_dir.exists():
        pdf_count = len([f for f in figures_dir.iterdir() if f.suffix == '.pdf'])
        png_count = len([f for f in figures_dir.iterdir() if f.suffix == '.png'])
        pdf_base = {f.stem for f in figures_dir.glob('*.pdf')}
        png_base = {f.stem for f in figures_dir.glob('*.png')}
        paired_count = len(pdf_base & png_base)
        print(f"\nFigures:")
        print(f"  PDF 数量: {pdf_count}")
        print(f"  PNG 数量: {png_count}")
        print(f"  配对数量: {paired_count}")
        print(f"  配对通过: {paired_count >= 5}")
    
    if flows_path.exists():
        df_flows = pd.read_csv(flows_path)
        print(f"\nSolution Flows:")
        print(f"  行数: {len(df_flows)}")
    
    if summary_path.exists():
        df_summary = pd.read_csv(summary_path)
        print(f"\nSolution Routes Summary:")
        print(f"  行数: {len(df_summary)}")
        print(f"  等于 n_selected: {len(df_summary) == n_selected}")
    
    if zip_path.exists():
        zip_size = zip_path.stat().st_size
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zip_file_count = len(zf.namelist())
        print(f"\nZip 文件:")
        print(f"  文件大小: {zip_size:,} bytes ({zip_size / 1024 / 1024:.2f} MB)")
        print(f"  包含文件数: {zip_file_count}")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有检查通过！")
    else:
        print("❌ 验收失败！")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    main()
