import os
from e2b import Sandbox

# Set API Key explicitly
os.environ["E2B_API_KEY"] = "e2b_54e1af0c8460650444c951ccdd726b21ec079152"

print("Testing e2b core library...")
try:
    # Attempt to create a base Sandbox (not code interpreter)
    sb = Sandbox(template="base") # 'base' is usually the default template
    print("Success: e2b.Sandbox created!")
    sb.close()
except Exception as e:
    print(f"Error with e2b.Sandbox: {type(e).__name__}: {e}")
