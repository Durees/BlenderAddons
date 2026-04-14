"""
面板定义 - 用户界面
"""

import bpy
from bpy.types import Panel, UIList
from bpy.props import StringProperty, BoolProperty, IntProperty

class MATERIAL_UL_validation_results(UIList):
    """验证结果列表"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # 自定义列表项绘制
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # 根据严重程度选择图标
            if item.severity == 1:
                icon = 'INFO'
            elif item.severity == 2:
                icon = 'ERROR'
            else:
                icon = 'CANCEL'
            
            # 主行
            row = layout.row(align=True)
            row.label(text=item.material_name, icon='MATERIAL')
            
            # 问题类型和描述
            split = layout.split(factor=0.3)
            split.label(text=item.issue_type)
            split.label(text=item.issue_description)
            
            # 操作按钮
            if item.node_name:
                op = row.operator("material.select_problem_node", 
                                 text="", icon='NODE')
                op.material_name = item.material_name
                op.node_name = item.node_name
        
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=icon)

class MATERIAL_PT_connection_validator(Panel):
    """材质连接验证器主面板"""
    bl_label = "材质连接验证器"
    bl_idname = "MATERIAL_PT_connection_validator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Material Tools"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 验证设置
        box = layout.box()
        box.label(text="验证设置", icon='SETTINGS')
        
        col = box.column(align=True)
        col.prop(context.scene, "material_validator_show_details")
        
        # 验证按钮
        row = layout.row()
        row.operator("material.validate_connections", 
                    text="验证所有材质", 
                    icon='CHECKMARK')
        
        # 结果显示
        if scene.material_validator_results:
            layout.separator()
            
            # 统计信息
            total = len(scene.material_validator_results)
            errors = sum(1 for r in scene.material_validator_results if r.severity >= 2)
            warnings = total - errors
            
            stats_box = layout.box()
            stats_row = stats_box.row()
            stats_row.label(text=f"发现 {total} 个问题", icon='ERROR')
            stats_row.label(text=f"错误: {errors}", icon='CANCEL')
            stats_row.label(text=f"警告: {warnings}", icon='INFO')
            
            # 结果列表
            layout.template_list(
                "MATERIAL_UL_validation_results",
                "",
                scene,
                "material_validator_results",
                scene,
                "material_validator_active_index"
            )
            
            # 操作按钮
            row = layout.row(align=True)
            row.operator("material.fix_missing_connections",
                        text="自动修复", 
                        icon='AUTO')
            row.operator("wm.operator_defaults",
                        text="清除结果", 
                        icon='TRASH').id = "material.validate_connections"
        
        # 帮助文本
        if not scene.material_validator_results:
            layout.separator()
            help_box = layout.box()
            help_box.label(text="使用说明:", icon='QUESTION')
            help_col = help_box.column(align=True)
            help_col.label(text="1. 点击'验证所有材质'开始检查")
            help_col.label(text="2. 查看检测到的问题列表")
            help_col.label(text="3. 点击节点名称可以快速定位")
            help_col.label(text="4. 使用自动修复尝试解决问题")

class MATERIAL_PT_validation_settings(Panel):
    """验证设置面板"""
    bl_label = "高级设置"
    bl_idname = "MATERIAL_PT_validation_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Material Tools"
    bl_parent_id = "MATERIAL_PT_connection_validator"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # 获取操作符属性
        op_props = layout.operator("material.validate_connections", text="")
        
        box = layout.box()
        box.label(text="检查选项", icon='FILTER')
        
        col = box.column(align=True)
        col.prop(op_props, "check_missing_connections")
        col.prop(op_props, "check_type_mismatch")
        col.prop(op_props, "check_cycles")
        col.prop(op_props, "check_unused_nodes")
        
        # 严重程度过滤
        box = layout.box()
        box.label(text="显示过滤", icon='VIEWZOOM')
        
        row = box.row(align=True)
        row.prop(context.scene, "material_validator_filter_severity", expand=True)
        
        # 材质类型过滤
        box = layout.box()
        box.label(text="材质类型", icon='MATERIAL')
        
        row = box.row(align=True)
        row.prop(context.scene, "material_validator_filter_cycles", text="Cycles", toggle=True)
        row.prop(context.scene, "material_validator_filter_eevee", text="Eevee", toggle=True)

class MATERIAL_PT_quick_fixes(Panel):
    """快速修复面板"""
    bl_label = "快速修复"
    bl_idname = "MATERIAL_PT_quick_fixes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Material Tools"
    bl_parent_id = "MATERIAL_PT_connection_validator"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="常见问题修复", icon='TOOL_SETTINGS')
        
        col = box.column(align=True)
        
        # 修复缺失颜色连接
        row = col.row(align=True)
        row.label(text="缺失颜色:", icon='NODE_MATERIAL')
        row.operator("material.fix_missing_color", 
                    text="添加默认颜色", 
                    icon='ADD')
        
        # 修复缺失法线连接
        row = col.row(align=True)
        row.label(text="缺失法线:", icon='NORMALS_FACE')
        row.operator("material.fix_missing_normal", 
                    text="添加法线贴图", 
                    icon='ADD')
        
        # 修复循环连接
        row = col.row(align=True)
        row.label(text="循环连接:", icon='LOOP_FORWARDS')
        row.operator("material.fix_cycle_connection", 
                    text="断开循环", 
                    icon='UNLINKED')
        
        # 批量修复
        layout.separator()
        row = layout.row()
        row.operator("material.fix_all_common_issues",
                    text="修复所有常见问题",
                    icon='CHECKMARK')

# 注册的类列表
classes = [
    MATERIAL_UL_validation_results,
    MATERIAL_PT_connection_validator,
    MATERIAL_PT_validation_settings,
    MATERIAL_PT_quick_fixes,
]

# 注册自定义属性
def register_properties():
    bpy.types.Scene.material_validator_active_index = IntProperty(
        name="活动索引",
        default=0
    )
    
    bpy.types.Scene.material_validator_filter_severity = EnumProperty(
        name="严重程度过滤",
        items=[
            ('ALL', "全部", "显示所有问题"),
            ('ERRORS', "仅错误", "只显示错误"),
            ('WARNINGS', "仅警告", "只显示警告"),
        ],
        default='ALL'
    )
    
    bpy.types.Scene.material_validator_filter_cycles = BoolProperty(
        name="Cycles材质",
        default=True
    )
    
    bpy.types.Scene.material_validator_filter_eevee = BoolProperty(
        name="Eevee材质",
        default=True
    )

def unregister_properties():
    del bpy.types.Scene.material_validator_active_index
    del bpy.types.Scene.material_validator_filter_severity
    del bpy.types.Scene.material_validator_filter_cycles
    del bpy.types.Scene.material_validator_filter_eevee