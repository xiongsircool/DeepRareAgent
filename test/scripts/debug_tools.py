"""
Minimal test to debug the StructuredTool callable issue
"""
from DeepRareAgent.tools import default_TOOL_EXCLUDE_LIST

# Check if tools are callable
for tool_name, tool_obj in default_TOOL_EXCLUDE_LIST.items():
    print(f"\n{tool_name}:")
    print(f"  Type: {type(tool_obj)}")
    print(f"  Callable: {callable(tool_obj)}")
    print(f"  Has 'invoke': {hasattr(tool_obj, 'invoke')}")
    print(f"  Has 'ainvoke': {hasattr(tool_obj, 'ainvoke')}")
    if hasattr(tool_obj, 'name'):
        print(f"  Tool name attr: {tool_obj.name}")
