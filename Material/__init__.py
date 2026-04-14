"""
Material Connection Validator - Blender插件
用于检测材质节点连接不正确的工具
"""

bl_info = {
    "name": "Material Connection Validator",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Material Tools",
    "description": "检测材质节点连接不正确的工具",
    "warning": "",
    "doc_url": "",
    "category": "Material",
}

import bpy
from bpy.types import Panel, Operator
from bpy.props import StringProperty, BoolProperty, IntProperty, CollectionProperty

# 导入模块
if "bpy" in locals():
    import importlib
    importlib.reload(operators)
    importlib.reload(panels)
    importlib.reload(utils)
else:
    from . import operators
    from . import panels
    from . import utils

# 注册类列表
classes = []

def register():
    # 注册所有类
    from .operators import classes as operator_classes
    from .panels import classes as panel_classes
    
    for cls in operator_classes + panel_classes:
        bpy.utils.register_class(cls)
        classes.append(cls)
    
    # 注册自定义属性
    from .panels import register_properties
    register_properties()
    
    bpy.types.Scene.material_validator_results = CollectionProperty(
        type=operators.MaterialValidationResult
    )
    bpy.types.Scene.material_validator_show_details = BoolProperty(
        name="显示详细信息",
        default=False
    )
    
    print("Material Connection Validator 插件已注册")

def unregister():
    # 注销所有类
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # 删除自定义属性
    from .panels import unregister_properties
    unregister_properties()
    
    del bpy.types.Scene.material_validator_results
    del bpy.types.Scene.material_validator_show_details
    
    print("Material Connection Validator 插件已注销")

if __name__ == "__main__":
    register()