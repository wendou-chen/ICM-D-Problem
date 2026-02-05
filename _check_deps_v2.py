import os
import sys
import ast
import importlib.util

# Common mappings from import name to pip package name
# Add more as discovered
PKG_MAP = {
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
    'scipy': 'scipy',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'torch': 'torch',
    'torchvision': 'torchvision',
    'tqdm': 'tqdm',
    'requests': 'requests',
    'psutil': 'psutil',
    'joblib': 'joblib',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'termcolor': 'termcolor',
    'pydot': 'pydot',
    'networkx': 'networkx',
    'h5py': 'h5py',
    'librosa': 'librosa',
    'numba': 'numba',
    'llvmlite': 'llvmlite',
    'soundfile': 'soundfile',
    'imageio': 'imageio',
    'tifffile': 'tifffile',
    'pywt': 'PyWavelets',
    'tensorboard': 'tensorboard',
    'protobuf': 'protobuf',
    'absl': 'absl-py',
    'google': 'protobuf', # often google.protobuf
}

def get_stdlib_names():
    if hasattr(sys, 'stdlib_module_names'):
        return sys.stdlib_module_names
    return sys.builtin_module_names

def is_local(name, root_path):
    # Check if name corresponds to a directory or file in root_path
    if os.path.exists(os.path.join(root_path, name)):
        return True
    if os.path.exists(os.path.join(root_path, name + '.py')):
        return True
    return False

def analyze_imports(root_dir):
    imports = set()
    
    for root, _, files in os.walk(root_dir):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                top_level = alias.name.split('.')[0]
                                imports.add(top_level)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                top_level = node.module.split('.')[0]
                                # Handle relative imports (level > 0)
                                if node.level == 0:
                                    imports.add(top_level)
                except Exception:
                    # Ignore parsing errors
                    pass
    return imports

def check_installed(module_name):
    # Try importing it
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

def main():
    root_dir = 'ai-watermark'
    
    # 1. Analyze code imports
    detected_imports = analyze_imports(root_dir)
    
    # 2. Filter
    stdlib = get_stdlib_names()
    # Also explicitly ignore local folders we saw in `ls`
    local_excludes = {'modules', 'systems', 'assets', 'datasets', 'utils', 'watermarkers', 'attack_configs', 'models'} 
    
    missing_packages = set()
    
    print("Analyzing imports...")
    for imp in detected_imports:
        if imp in stdlib:
            continue
        if imp in local_excludes:
            continue
        if is_local(imp, root_dir):
            continue
            
        # Check if installed
        if not check_installed(imp):
            # Map to package name
            pkg = PKG_MAP.get(imp, imp)
            missing_packages.add(pkg)
            
    # Output missing packages
    if missing_packages:
        print("MISSING_PACKAGES_START")
        for pkg in sorted(missing_packages):
            print(pkg)
        print("MISSING_PACKAGES_END")
    else:
        print("NO_MISSING_PACKAGES")

if __name__ == '__main__':
    main()
