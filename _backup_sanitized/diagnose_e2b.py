import os
import sys
from importlib.metadata import version
from e2b_code_interpreter import Sandbox

# Print version info
print(f"Python: {sys.version}")
try:
    print(f"e2b-code-interpreter: {version('e2b-code-interpreter')}")
    print(f"e2b: {version('e2b')}")
except Exception as e:
    print(f"Error getting versions: {e}")

# Use API Key from environment variable
API_KEY = os.getenv("E2B_API_KEY", "YOUR_E2B_API_KEY_HERE")

print("\nAttempting to initialize Sandbox with explicit API Key...")
try:
    # Try without parameters (except Key)
    sb = Sandbox(api_key=API_KEY)
    print("SUCCESS: Sandbox initialized!")
    sb.close()
except TypeError as e:
    print(f"\nCRITICAL ERROR: TypeError detected.")
    print(f"Details: {e}")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
