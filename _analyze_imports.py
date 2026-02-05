import os
import ast
import sys
import importlib.util

# Mapping from import name to likely pip package name
pkg_map = {
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'sklearn': 'scikit-learn',
    'skimage': 'scikit-image',
    'bs4': 'beautifulsoup4',
    'dateutil': 'python-dateutil',
    'dotenv': 'python-dotenv',
    'fitz': 'pymupdf',
    'hydra': 'hydra-core',
    'mpl_toolkits': 'matplotlib',
    'torcheval': 'torcheval',
    'lpips': 'lpips',
    'kornia': 'kornia',
    'diffusers': 'diffusers',
    'timm': 'timm',
    'invisible_watermark': 'invisible-watermark',
    'omegaconf': 'omegaconf',
    'einops': 'einops',
    'albumentations': 'albumentations',
    'onnxruntime': 'onnxruntime',
    'onnx': 'onnx',
    'safetensors': 'safetensors',
    'transformers': 'transformers',
    'accelerate': 'accelerate',
    'pytorch_lightning': 'pytorch-lightning',
    'wandb': 'wandb',
    'moviepy': 'moviepy',
    'proglog': 'proglog',
}

def get_imports_from_dir(start_dir):
    imports = set()
    local_modules = set()
    
    # First, identify local modules (directories with __init__.py or .py files) in the root of ai-watermark
    # But imports might be absolute based on PYTHONPATH. 
    # The grep output showed "from modules.attack import ...", implying 'modules' is a top level package relative to execution or source root.
    
    # Let's walk and parse
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        tree = ast.parse(f.read())
                except Exception as e:
                    print(f"Error parsing {path}: {e}", file=sys.stderr)
                    continue
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            root_pkg = alias.name.split('.')[0]
                            imports.add(root_pkg)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            root_pkg = node.module.split('.')[0]
                            imports.add(root_pkg)
    
    return imports

def main():
    target_dir = 'ai-watermark'
    if not os.path.exists(target_dir):
        print(f"Directory {target_dir} not found.")
        return

    found_imports = get_imports_from_dir(target_dir)
    
    # Identify local folders in ai-watermark to exclude them
    local_items = set(os.listdir(target_dir))
    
    missing_pkgs = set()
    
    # Standard library check
    stdlib = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else sys.builtin_module_names

    for imp in found_imports:
        if imp in local_items:
            continue
        if imp in stdlib:
            continue
        if imp in ['modules', 'watermarkers', 'utils', 'models']: # Heuristic for common local folders
            continue
            
        # Check if installed
        spec = importlib.util.find_spec(imp)
        if spec is None:
            # Try mapping
            mapped = pkg_map.get(imp, imp)
            # Check mapped again just in case (e.g. PIL vs Pillow installed)
            # importlib.util.find_spec('PIL') works if Pillow is installed
            # So if find_spec(imp) failed, we assume we need to install it.
            missing_pkgs.add(mapped)
            
    # Remove known built-ins that might have slipped or local things
    # Filter out empty
    missing_pkgs = {p for p in missing_pkgs if p}
    
    print('\n'.join(sorted(missing_pkgs)))

if __name__ == '__main__':
    main()
