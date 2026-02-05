
import os

file_path = os.path.abspath("scripts/viz_q4_detailed.py")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Change tick direction
if "direction='out'" in content:
    content = content.replace("direction='out'", "direction='in'")
    print("Updated tick direction.")
else:
    print("tick direction not found or already updated.")

# 2. Remove fontweight='bold'
if ", fontweight='bold'" in content:
    content = content.replace(", fontweight='bold'", "")
    print("Removed bold font weights.")
else:
    print("fontweight='bold' not found.")

# 3. Change title vs. to vs
if "Construction vs. Operation" in content:
    content = content.replace("Construction vs. Operation", "Construction vs Operation")
    print("Updated title.")
else:
    print("Title string not found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
