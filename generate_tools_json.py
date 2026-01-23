"""生成 tools.json 和 tools_test.json"""
from tool_schemas import write_tools_json

write_tools_json("tools.json", include_test=False)
print("Generated: tools.json")

write_tools_json("tools_test.json", include_test=True)
print("Generated: tools_test.json")
