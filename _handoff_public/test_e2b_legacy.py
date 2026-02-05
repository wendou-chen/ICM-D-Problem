import os
from e2b_code_interpreter import Sandbox

# Set API Key from environment variable
api_key = os.getenv("E2B_API_KEY", "YOUR_E2B_API_KEY_HERE")

print(f"Testing E2B (Legacy Version 1.x)...")

try:
    # In v1.x, api_key was often passed directly or via env var
    # We'll try explicit passing first
    with Sandbox(api_key=api_key) as sandbox:
        print("Success: Sandbox initialized!")
        
        code = "import math; print(f'Pi is approximately {math.pi:.4f}')"
        execution = sandbox.run_code(code)
        
        print(f"Output: {execution.logs.stdout}")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
