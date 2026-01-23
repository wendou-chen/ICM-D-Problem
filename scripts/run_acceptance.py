"""
直接运行验收测试（不依赖subprocess）
"""
import json
import sys
import zipfile
from pathlib import Path

# 添加scripts目录到路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

# 先运行viz_task2
print("=" * 80)
print("步骤1: 运行 viz_task2.py")
print("=" * 80)

try:
    import viz_task2
    # 手动调用main，但需要模拟argparse
    class Args:
        outdir = "outputs/task2/viz"
        run_id = "auto"
        edge_sample = 20000
        dpi = 200
        fmt = "pdf,png"
    
    # 保存原始的sys.argv
    original_argv = sys.argv
    try:
        sys.argv = ['viz_task2.py'] + [
            '--outdir', Args.outdir,
            '--run_id', Args.run_id,
            '--edge_sample', str(Args.edge_sample),
            '--dpi', str(Args.dpi),
            '--fmt', Args.fmt
        ]
        viz_task2.main()
    finally:
        sys.argv = original_argv
except Exception as e:
    print(f"运行 viz_task2 时出错: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 然后运行验收检查
print("\n" + "=" * 80)
print("步骤2: 运行验收检查")
print("=" * 80)

sys.path.insert(0, str(ROOT_DIR))
import validate_viz_task2
success = validate_viz_task2.run_acceptance_test()

sys.exit(0 if success else 1)
