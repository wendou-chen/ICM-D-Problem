import os
import sys
from importlib.metadata import version
from e2b_code_interpreter import Sandbox

# 打印版本信息
print(f"Python: {sys.version}")
try:
    print(f"e2b-code-interpreter: {version('e2b-code-interpreter')}")
    print(f"e2b: {version('e2b')}")
except Exception as e:
    print(f"Error getting versions: {e}")

# 显式使用 Key
API_KEY = "e2b_54e1af0c8460650444c951ccdd726b21ec079152"

print("\nAttempting to initialize Sandbox with explicit API Key...")
try:
    # 尝试不带参数（除了 Key）
    sb = Sandbox(api_key=API_KEY)
    print("SUCCESS: Sandbox initialized!")
    sb.close()
except TypeError as e:
    print(f"\nCRITICAL ERROR: TypeError detected.")
    print(f"Details: {e}")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
