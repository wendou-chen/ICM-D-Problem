"""
acceptance_test.py
一键运行验收测试（不依赖命令行）
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

# 设置路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

# 导入viz_task2
import viz_task2


def run_viz_task2():
    """运行viz_task2"""
    print("=" * 80)
    print("[步骤1] 运行 viz_task2.py")
    print("=" * 80)
    
    try:
        # 模拟argparse参数
        class Args:
            outdir = "outputs/task2/viz"
            run_id = "auto"
            edge_sample = 20000
            dpi = 200
            fmt = "pdf,png"
        
        args = Args()
        
        # 保存原始sys.argv
        original_argv = sys.argv
        try:
            sys.argv = ['viz_task2.py',
                       '--outdir', args.outdir,
                       '--run_id', args.run_id,
                       '--edge_sample', str(args.edge_sample),
                       '--dpi', str(args.dpi),
                       '--fmt', args.fmt]
            
            viz_task2.main()
            print("\n✅ viz_task2.py 执行成功")
            return True
        finally:
            sys.argv = original_argv
            
    except Exception as e:
        print(f"\n❌ 运行 viz_task2.py 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_acceptance_checks():
    """运行验收检查"""
    print("\n" + "=" * 80)
    print("[步骤2] 运行验收检查")
    print("=" * 80)
    
    # 加载 best_solution.json
    best_sol_path = ROOT_DIR / "outputs" / "task2" / "best_solution.json"
    if not best_sol_path.exists():
        print(f"❌ best_solution.json 不存在: {best_sol_path}")
        return False
    
    with open(best_sol_path, 'r', encoding='utf-8') as f:
        best_sol = json.load(f)
    
    run_id = best_sol.get("run_id")
    selected_ids = best_sol.get("selected_ids", [])
    n_selected = best_sol.get("n_selected", len(selected_ids))
    
    outdir = ROOT_DIR / "outputs" / "task2" / "viz"
    all_passed = True
    
    # A) figures 目录检查
    print("\n" + "-" * 80)
    print("[2A] figures 目录图数量检查")
    print("-" * 80)
    
    figures_dir = outdir / "figures"
    if not figures_dir.exists():
        print(f"❌ figures 目录不存在: {figures_dir}")
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
        
        # 检查配对
        pdf_basenames = {f[:-4] for f in pdf_files}
        png_basenames = {f[:-4] for f in png_files}
        
        paired = pdf_basenames & png_basenames
        pdf_only = pdf_basenames - png_basenames
        png_only = png_basenames - pdf_basenames
        
        print(f"\n配对检查:")
        print(f"  配对成功: {len(paired)} 对")
        if pdf_only:
            print(f"  ❌ 只有 PDF 无 PNG: {sorted(pdf_only)}")
            all_passed = False
        if png_only:
            print(f"  ❌ 只有 PNG 无 PDF: {sorted(png_only)}")
            all_passed = False
        
        # 验收标准
        if len(pdf_files) < 5:
            print(f"\n❌ PDF 文件数 ({len(pdf_files)}) < 5")
            all_passed = False
        if len(png_files) < 5:
            print(f"\n❌ PNG 文件数 ({len(png_files)}) < 5")
            all_passed = False
        if len(paired) < 5:
            print(f"\n❌ 配对数量 ({len(paired)}) < 5")
            all_passed = False
        
        if all_passed:
            print("\n✅ figures 目录检查通过")
    
    # B) solution_flows.csv 检查
    print("\n" + "-" * 80)
    print("[2B] solution_flows.csv 检查")
    print("-" * 80)
    
    flows_path = outdir / "solution_flows.csv"
    if not flows_path.exists():
        print(f"❌ solution_flows.csv 不存在: {flows_path}")
        all_passed = False
    else:
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
        
        if actual_cols != expected_cols:
            print(f"\n❌ 列名不匹配!")
            print(f"  期望: {expected_cols}")
            print(f"  实际: {actual_cols}")
            all_passed = False
        else:
            print("\n✅ 列名匹配")
        
        if n_selected > 0 and row_count == 0:
            print(f"\n❌ selected_ids 非空但 solution_flows.csv 行数为 0")
            all_passed = False
        elif row_count > 0:
            print("\n前 3 行:")
            print(df_flows.head(3).to_string())
            print("\n✅ solution_flows.csv 检查通过")
    
    # C) solution_routes_summary.csv 检查
    print("\n" + "-" * 80)
    print("[2C] solution_routes_summary.csv 检查")
    print("-" * 80)
    
    summary_path = outdir / "solution_routes_summary.csv"
    if not summary_path.exists():
        print(f"❌ solution_routes_summary.csv 不存在: {summary_path}")
        all_passed = False
    else:
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
        
        if actual_cols != expected_cols:
            print(f"\n❌ 列名不匹配!")
            print(f"  期望: {expected_cols}")
            print(f"  实际: {actual_cols}")
            all_passed = False
        else:
            print("\n✅ 列名匹配")
        
        if row_count != n_selected:
            print(f"\n❌ 行数 ({row_count}) != n_selected ({n_selected})")
            all_passed = False
        else:
            print(f"\n✅ 行数匹配 n_selected ({n_selected})")
        
        if row_count > 0:
            print("\n前 3 行:")
            print(df_summary.head(3).to_string())
            print("\n✅ solution_routes_summary.csv 检查通过")
    
    # D) README_for_artist.md 检查
    print("\n" + "-" * 80)
    print("[2D] README_for_artist.md 检查")
    print("-" * 80)
    
    readme_path = outdir / "README_for_artist.md"
    if not readme_path.exists():
        print(f"❌ README_for_artist.md 不存在: {readme_path}")
        all_passed = False
    else:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        print(f"\n文件路径: {readme_path}")
        print(f"总行数: {len(lines)}")
        print("\n前 40 行:")
        for i, line in enumerate(lines[:40], 1):
            print(f"{i:3d}: {line}")
        
        # 检查关键词
        has_kepler = "Kepler" in content
        has_convergence = "收敛曲线建议" in content or "convergence" in content.lower()
        
        print(f"\n关键词检查:")
        print(f"  包含 'Kepler': {has_kepler}")
        print(f"  包含 '收敛曲线建议': {has_convergence}")
        
        print("\n✅ README_for_artist.md 检查通过")
    
    # E) zip 文件检查
    print("\n" + "-" * 80)
    print("[2E] plot_pack_{run_id}.zip 检查")
    print("-" * 80)
    
    zip_path = outdir / f"plot_pack_{run_id}.zip"
    if not zip_path.exists():
        print(f"❌ zip 文件不存在: {zip_path}")
        all_passed = False
    else:
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
            
            # 检查必需文件
            print("\n必需文件检查:")
            missing_files = []
            for req_file in required_files:
                # 可能在根目录或子目录
                found = any(req_file in f for f in zip_files)
                if found:
                    matching = [f for f in zip_files if req_file in f]
                    print(f"  ✅ {req_file} (在: {matching[0] if matching else 'N/A'})")
                else:
                    print(f"  ❌ {req_file} 缺失")
                    missing_files.append(req_file)
            
            # 检查 figures
            pdf_in_zip = [f for f in zip_files if f.endswith('.pdf')]
            png_in_zip = [f for f in zip_files if f.endswith('.png')]
            
            print(f"\nZip 内的图表文件:")
            print(f"  PDF: {len(pdf_in_zip)} 个")
            print(f"  PNG: {len(png_in_zip)} 个")
            
            if len(pdf_in_zip) < 5:
                print(f"  ❌ PDF 文件数 ({len(pdf_in_zip)}) < 5")
                all_passed = False
            if len(png_in_zip) < 5:
                print(f"  ❌ PNG 文件数 ({len(png_in_zip)}) < 5")
                all_passed = False
            
            if missing_files:
                print(f"\n❌ 缺失必需文件: {missing_files}")
                all_passed = False
            else:
                print("\n✅ zip 文件检查通过")
    
    # [3] 最终验收报告
    print("\n" + "=" * 80)
    print("[步骤3] 最终验收报告")
    print("=" * 80)
    
    print(f"\nRun ID: {run_id}")
    print(f"Selected IDs: {selected_ids}")
    print(f"N Selected: {n_selected}")
    
    if figures_dir.exists():
        pdf_count = len([f for f in figures_dir.iterdir() if f.suffix == '.pdf'])
        png_count = len([f for f in figures_dir.iterdir() if f.suffix == '.png'])
        pdf_basenames = {f.stem for f in figures_dir.glob('*.pdf')}
        png_basenames = {f.stem for f in figures_dir.glob('*.png')}
        paired_count = len(pdf_basenames & png_basenames)
        print(f"\nFigures:")
        print(f"  PDF 数量: {pdf_count}")
        print(f"  PNG 数量: {png_count}")
        print(f"  配对数量: {paired_count}")
        print(f"  配对通过: {paired_count >= 5}")
    else:
        print("\nFigures: ❌ 目录不存在")
    
    if flows_path.exists():
        df_flows = pd.read_csv(flows_path)
        print(f"\nSolution Flows:")
        print(f"  行数: {len(df_flows)}")
    else:
        print("\nSolution Flows: ❌ 文件不存在")
    
    if summary_path.exists():
        df_summary = pd.read_csv(summary_path)
        print(f"\nSolution Routes Summary:")
        print(f"  行数: {len(df_summary)}")
        print(f"  等于 n_selected: {len(df_summary) == n_selected}")
    else:
        print("\nSolution Routes Summary: ❌ 文件不存在")
    
    if zip_path.exists():
        zip_size = zip_path.stat().st_size
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zip_file_count = len(zf.namelist())
        print(f"\nZip 文件:")
        print(f"  文件大小: {zip_size:,} bytes ({zip_size / 1024 / 1024:.2f} MB)")
        print(f"  包含文件数: {zip_file_count}")
    else:
        print("\nZip 文件: ❌ 不存在")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有检查通过！")
        return True
    else:
        print("❌ 验收失败！请检查上述错误。")
        return False


def main():
    """主函数"""
    # 运行viz_task2
    if not run_viz_task2():
        print("\n❌ viz_task2 执行失败，终止验收")
        sys.exit(1)
    
    # 运行验收检查
    if not run_acceptance_checks():
        print("\n❌ 验收检查失败")
        sys.exit(1)
    
    print("\n✅ 验收测试全部通过！")
    sys.exit(0)


if __name__ == "__main__":
    main()
