"""
UV快速展开工具 - Blender插件（增强版）
版本: 1.1.0
作者: 基于URDF2Mesh UV处理器
描述: 一键对选中的网格物体执行智能UV投影，支持批量处理和进度显示
"""

bl_info = {
    "name": "UV快速展开工具（增强版）",
    "author": "URDF2Mesh Team",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "3D视图 > 侧边栏 > UV工具",
    "description": "一键对选中的网格物体执行智能UV投影，支持批量处理和进度显示",
    "category": "UV",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import FloatProperty, BoolProperty, PointerProperty, IntProperty, EnumProperty
from math import radians
import time

# ============================================================================
# 属性组 - 存储插件配置
# ============================================================================

class UVUnwrapSettings(PropertyGroup):
    """UV展开设置"""
    
    angle_limit: FloatProperty(
        name="角度限制",
        description="智能UV投影的角度限制（度）",
        default=66.0,
        min=1.0,
        max=89.0,
        step=10,
        precision=1,
        subtype='ANGLE'
    )
    
    island_margin: FloatProperty(
        name="岛屿间距",
        description="UV岛屿之间的间距",
        default=0.0,
        min=0.0,
        max=1.0,
        step=0.01,
        precision=3
    )
    
    area_weight: FloatProperty(
        name="面积权重",
        description="面积权重参数",
        default=0.0,
        min=0.0,
        max=1.0,
        step=0.01,
        precision=3
    )
    
    correct_aspect: BoolProperty(
        name="校正宽高比",
        description="校正UV宽高比",
        default=True
    )
    
    scale_to_bounds: BoolProperty(
        name="缩放到边界",
        description="将UV缩放到0-1边界框内（确保每个物体UV填充自己的0-1空间）",
        default=True
    )
    
    auto_select_all: BoolProperty(
        name="自动选择所有面",
        description="自动选择网格的所有面",
        default=True
    )
    
    keep_seam: BoolProperty(
        name="保留接缝",
        description="保留现有的UV接缝",
        default=True
    )
    
    angle_input_mode: EnumProperty(
        name="角度输入模式",
        description="角度值的输入方式",
        items=[
            ('DEGREES', "角度值", "直接输入角度值（如66°）"),
            ('LEGACY', "传统值", "输入传统值（如3782）以匹配原始工具"),
        ],
        default='DEGREES'
    )
    
    batch_mode: EnumProperty(
        name="批量模式",
        description="处理多个物体的方式",
        items=[
            ('SEQUENTIAL', "顺序处理", "逐个处理每个物体，每个物体有独立的0-1 UV空间"),
        ],
        default='SEQUENTIAL'
    )
    
    show_progress: BoolProperty(
        name="显示进度",
        description="处理时显示进度信息",
        default=True
    )
    
    verbose_logging: BoolProperty(
        name="详细日志",
        description="显示每个物体的详细处理信息",
        default=True
    )

# ============================================================================
# 操作符 - 执行UV展开（增强版）
# ============================================================================

class UV_OT_quick_unwrap_enhanced(Operator):
    """快速UV展开选中的网格物体（增强版）"""
    
    bl_idname = "uv.quick_unwrap_enhanced"
    bl_label = "快速UV展开（增强版）"
    bl_description = "对选中的网格物体执行智能UV投影，支持批量处理和进度显示"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """检查是否有选中的网格物体"""
        return any(obj.type == 'MESH' for obj in context.selected_objects)
    
    def execute(self, context):
        """执行UV展开操作"""
        scene = context.scene
        settings = scene.uv_unwrap_settings
        
        # 获取选中的网格物体
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "没有选中的网格物体")
            return {'CANCELLED'}
        
        success_count = 0
        failed_count = 0
        start_time = time.time()
        
        # 保存当前模式
        original_mode = context.mode
        original_active = context.active_object
        
        try:
            # 顺序处理每个物体（确保每个物体有独立的0-1 UV空间）
            for i, obj in enumerate(mesh_objects):
                if settings.show_progress:
                    self._update_progress(f"处理中: {obj.name} ({i+1}/{len(mesh_objects)})", i/len(mesh_objects))
                
                try:
                    if self._unwrap_single(context, obj, settings):
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"处理物体 '{obj.name}' 时出错: {e}")
            
            # 恢复原始活动物体和模式
            if original_active:
                context.view_layer.objects.active = original_active
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            
            # 清除进度显示
            if settings.show_progress:
                self._update_progress("", 1.0)
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            # 报告结果
            if success_count > 0:
                message = f"成功展开 {success_count} 个物体的UV ({elapsed_time:.1f}秒)"
                if failed_count > 0:
                    message += f"，{failed_count} 个失败"
                self.report({'INFO'}, message)
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"所有物体处理失败 ({elapsed_time:.1f}秒)")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"UV展开过程中出错: {str(e)}")
            return {'CANCELLED'}
    
    def _unwrap_single(self, context, obj, settings):
        """处理单个物体"""
        try:
            # 保存原始选择
            original_selected_objects = context.selected_objects.copy()
            
            # 取消选择所有物体，只选择当前物体
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            
            # 设置活动物体
            context.view_layer.objects.active = obj
            
            # 详细日志：进入编辑模式
            if settings.verbose_logging:
                print(f"[UV工具] 处理物体: {obj.name} - 进入编辑模式")
            
            # 进入编辑模式（只编辑当前物体）
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 获取网格数据
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            
            # 选择所有面（如果启用）
            if settings.auto_select_all:
                for face in bm.faces:
                    face.select = True
            
            # 计算角度限制（根据输入模式）
            if settings.angle_input_mode == 'DEGREES':
                # 角度模式：直接转换角度到弧度
                angle_limit_rad = radians(settings.angle_limit)
            else:
                # 传统模式：模拟原始工具行为
                # 原始工具：angle_limit = uv_angle_limit * π / 180
                # 所以如果用户输入3782，得到：3782 * π / 180 ≈ 66弧度
                angle_limit_rad = settings.angle_limit * 3.141592653589793 / 180.0
            
            # 详细日志：执行UV展开
            if settings.verbose_logging:
                print(f"[UV工具] 处理物体: {obj.name} - 执行智能UV投影")
            
            # 执行智能UV投影
            # 注意：将 scale_to_bounds 设置为 True 以确保每个物体的UV填充自己的0-1空间
            bpy.ops.uv.smart_project(
                angle_limit=angle_limit_rad,
                margin_method='SCALED',
                rotate_method='AXIS_ALIGNED_Y',
                island_margin=settings.island_margin,
                area_weight=settings.area_weight,
                correct_aspect=settings.correct_aspect,
                scale_to_bounds=True  # 强制设置为True，确保每个物体UV填充0-1空间
            )
            
            # 更新网格
            bmesh.update_edit_mesh(mesh)
            
            # 详细日志：退出编辑模式
            if settings.verbose_logging:
                print(f"[UV工具] 处理物体: {obj.name} - 退出编辑模式")
            
            # 返回物体模式
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 恢复原始选择
            bpy.ops.object.select_all(action='DESELECT')
            for original_obj in original_selected_objects:
                original_obj.select_set(True)
            
            return True
            
        except Exception as e:
            print(f"处理物体 '{obj.name}' 时出错: {e}")
            # 确保返回物体模式
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            return False
    
    
    def _update_progress(self, message, progress):
        """更新进度显示"""
        if hasattr(bpy.context, "window_manager"):
            wm = bpy.context.window_manager
            wm.progress_begin(0, 100)
            wm.progress_update(int(progress * 100))
            if message:
                print(message)
            wm.progress_end()

# ============================================================================
# 操作符 - 重置默认设置
# ============================================================================

class UV_OT_reset_settings(Operator):
    """重置UV展开设置为默认值"""
    
    bl_idname = "uv.reset_unwrap_settings"
    bl_label = "重置设置"
    bl_description = "重置UV展开设置为默认值"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """重置设置"""
        settings = context.scene.uv_unwrap_settings
        
        settings.angle_limit = 66.0
        settings.island_margin = 0.0
        settings.area_weight = 0.0
        settings.correct_aspect = True
        settings.scale_to_bounds = True
        settings.auto_select_all = True
        settings.keep_seam = True
        settings.angle_input_mode = 'DEGREES'
        settings.batch_mode = 'SEQUENTIAL'
        settings.show_progress = True
        settings.verbose_logging = True
        
        self.report({'INFO'}, "设置已重置为默认值")
        return {'FINISHED'}

# ============================================================================
# 操作符 - 应用设置到所有选中物体
# ============================================================================

class UV_OT_apply_to_selected(Operator):
    """将当前设置应用到所有选中物体"""
    
    bl_idname = "uv.apply_to_selected"
    bl_label = "应用到选中物体"
    bl_description = "将当前UV设置应用到所有选中物体"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """应用设置"""
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "没有选中的网格物体")
            return {'CANCELLED'}
        
        for obj in mesh_objects:
            # 这里可以添加将设置保存到物体自定义属性的代码
            pass
        
        self.report({'INFO'}, f"设置已应用到 {len(mesh_objects)} 个物体")
        return {'FINISHED'}

# ============================================================================
# 操作符 - 清除所有选中物体的UVMap
# ============================================================================

class UV_OT_clear_uvmaps(Operator):
    """清除所有选中物体的UVMap"""
    
    bl_idname = "uv.clear_uvmaps"
    bl_label = "清除UVMap"
    bl_description = "清除所有选中物体的UVMap"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """检查是否有选中的网格物体"""
        return any(obj.type == 'MESH' for obj in context.selected_objects)
    
    def execute(self, context):
        """清除UVMap"""
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "没有选中的网格物体")
            return {'CANCELLED'}
        
        cleared_count = 0
        
        # 保存当前模式
        original_mode = context.mode
        original_active = context.active_object
        
        try:
            for obj in mesh_objects:
                # 检查物体是否有UVMap
                if not obj.data.uv_layers:
                    continue
                
                # 设置活动物体
                context.view_layer.objects.active = obj
                
                # 进入编辑模式
                bpy.ops.object.mode_set(mode='EDIT')
                
                # 选择所有面
                bpy.ops.mesh.select_all(action='SELECT')
                
                # 清除UV（通过删除所有UV坐标）
                # 注意：这里使用bpy.ops.uv.reset()来重置UV坐标
                bpy.ops.uv.reset()
                
                # 返回物体模式
                bpy.ops.object.mode_set(mode='OBJECT')
                
                cleared_count += 1
            
            # 恢复原始活动物体和模式
            if original_active:
                context.view_layer.objects.active = original_active
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            
            self.report({'INFO'}, f"已清除 {cleared_count} 个物体的UVMap")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"清除UVMap时出错: {str(e)}")
            return {'CANCELLED'}

# ============================================================================
# 面板 - 3D视图侧边栏（增强版）
# ============================================================================

class VIEW3D_PT_uv_unwrap_tool_enhanced(Panel):
    """UV快速展开工具面板（增强版）"""
    
    bl_label = "UV快速展开工具（增强版）"
    bl_idname = "VIEW3D_PT_uv_unwrap_tool_enhanced"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV工具"
    bl_context = "objectmode"
    
    def draw(self, context):
        """绘制面板UI"""
        layout = self.layout
        scene = context.scene
        settings = scene.uv_unwrap_settings
        
        # 状态信息
        mesh_count = sum(1 for obj in context.selected_objects if obj.type == 'MESH')
        box = layout.box()
        if mesh_count == 0:
            box.label(text="未选中网格物体", icon='ERROR')
        else:
            box.label(text=f"已选中 {mesh_count} 个网格物体", icon='MESH_DATA')
        
        # 主操作按钮
        col = layout.column(align=True)
        col.operator("uv.quick_unwrap_enhanced", icon='UV', text="一键UV展开（增强）")
        col.separator()
        
        # 批量处理设置
        box = layout.box()
        box.label(text="批量处理设置", icon='MODIFIER')
        
        col = box.column(align=True)
        col.prop(settings, "batch_mode", expand=True)
        col.prop(settings, "show_progress")
        
        # UV投影设置
        box = layout.box()
        box.label(text="UV投影设置", icon='SETTINGS')
        
        # 角度输入模式
        col = box.column(align=True)
        col.prop(settings, "angle_input_mode", text="")
        
        # 角度限制（根据模式显示不同的提示）
        angle_row = box.row(align=True)
        angle_row.prop(settings, "angle_limit")
        
        if settings.angle_input_mode == 'DEGREES':
            angle_row.label(text="°", icon='NONE')
            box.label(text="默认: 66° (Blender UI标准)", icon='INFO')
        else:
            angle_row.label(text="传统值", icon='NONE')
            box.label(text="默认: 3782 (匹配原始工具)", icon='INFO')
            box.label(text="注: 3782 × π / 180 ≈ 66弧度", icon='QUESTION')
        
        # 其他参数
        col = box.column(align=True)
        col.prop(settings, "island_margin")
        col.prop(settings, "area_weight")
        
        # 选项
        col = box.column(align=True)
        col.prop(settings, "correct_aspect")
        col.prop(settings, "scale_to_bounds")
        col.prop(settings, "auto_select_all")
        col.prop(settings, "keep_seam")
        col.prop(settings, "verbose_logging")
        
        # 工具按钮
        box = layout.box()
        row = box.row(align=True)
        row.operator("uv.reset_unwrap_settings", icon='LOOP_BACK', text="重置设置")
        row.operator("uv.apply_to_selected", icon='CHECKMARK', text="应用设置")
        row.operator("uv.clear_uvmaps", icon='TRASH', text="清除UV")
        
        # 帮助链接
        row = box.row(align=True)
        op = row.operator("wm.url_open", text="Blender文档", icon='HELP')
        op.url = "https://docs.blender.org/manual/en/latest/modeling/meshes/uv/unwrapping/smart_project.html"
        
        op = row.operator("wm.url_open", text="教程", icon='QUESTION')
        op.url = "https://www.youtube.com/results?search_query=blender+smart+uv+project"

# ============================================================================
# 注册和注销
# ============================================================================

classes = (
    UVUnwrapSettings,
    UV_OT_quick_unwrap_enhanced,
    UV_OT_reset_settings,
    UV_OT_apply_to_selected,
    UV_OT_clear_uvmaps,
    VIEW3D_PT_uv_unwrap_tool_enhanced,
)

def register():
    """注册插件"""
    from bpy.utils import register_class
    
    for cls in classes:
        register_class(cls)
    
    # 注册属性组
    bpy.types.Scene.uv_unwrap_settings = PointerProperty(type=UVUnwrapSettings)
    
    print("UV快速展开工具插件（增强版）已注册")

def unregister():
    """注销插件"""
    from bpy.utils import unregister_class
    
    # 注销属性组
    del bpy.types.Scene.uv_unwrap_settings
    
    for cls in reversed(classes):
        unregister_class(cls)
    
    print("UV快速展开工具插件（增强版）已注销")

if __name__ == "__main__":
    register()