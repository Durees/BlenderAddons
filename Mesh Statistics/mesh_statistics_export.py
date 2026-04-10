bl_info = {
    "name": "网格统计导出器",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Mesh Stats",
    "description": "计算选中网格的面数(F)、顶点数(V)、边数(E)并导出为CSV文件",
    "category": "Mesh",
}

import bpy
import csv
import os
from bpy.types import Panel, Operator
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ExportHelper

class MESH_OT_calculate_multiple_stats(Operator):
    """计算多个选中网格的统计数据"""
    bl_idname = "mesh.calculate_multiple_stats"
    bl_label = "计算多个网格统计"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取所有选中的网格对象
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'ERROR'}, "请选择至少一个网格对象")
            return {'CANCELLED'}
        
        # 存储统计数据
        stats_data = []
        
        for obj in selected_objects:
            mesh = obj.data
            
            # 计算基本统计数据
            F = len(mesh.polygons)  # 面数
            V = len(mesh.vertices)  # 顶点数
            E = len(mesh.edges)     # 边数
            
            # 计算比值
            if F > 0:
                vf_ratio = V / F
                ef_ratio = E / F
            else:
                vf_ratio = 0.0
                ef_ratio = 0.0
            
            # 计算X = V - E + F
            X = V - E + F
            
            # 计算g = 1 - X/2
            g = 1 - X / 2
            
            stats_data.append({
                'name': obj.name,
                'F': F,
                'V': V,
                'E': E,
                'V/F': vf_ratio,
                'E/F': ef_ratio,
                'X': X,
                'g': g
            })
        
        # 存储到场景属性中
        scene = context.scene
        scene.mesh_stats_data = str(stats_data)  # 存储为字符串以便保存
        
        self.report({'INFO'}, f"计算完成: 共{len(stats_data)}个对象")
        return {'FINISHED'}

class MESH_OT_export_stats_csv(Operator, ExportHelper):
    """导出网格统计数据为CSV文件"""
    bl_idname = "mesh.export_stats_csv"
    bl_label = "导出CSV"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".csv"
    
    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    include_ratios: BoolProperty(
        name="包含比值",
        description="包含V/F和E/F比值",
        default=True,
    )
    
    include_formulas: BoolProperty(
        name="包含公式计算",
        description="包含X值和g值",
        default=True,
    )
    
    def execute(self, context):
        scene = context.scene
        
        # 检查是否有统计数据
        if not hasattr(scene, 'mesh_stats_data') or not scene.mesh_stats_data:
            self.report({'ERROR'}, "请先计算网格统计数据")
            return {'CANCELLED'}
        
        try:
            # 解析存储的数据
            import ast
            stats_data = ast.literal_eval(scene.mesh_stats_data)
        except:
            self.report({'ERROR'}, "统计数据格式错误，请重新计算")
            return {'CANCELLED'}
        
        if not stats_data:
            self.report({'ERROR'}, "没有可导出的数据")
            return {'CANCELLED'}
        
        # 准备CSV数据
        csv_data = []
        
        # 表头
        headers = ['部件名称', '面数(F)', '顶点数(V)', '边数(E)']
        if self.include_ratios:
            headers.extend(['V/F比值', 'E/F比值'])
        if self.include_formulas:
            headers.extend(['X值(V-E+F)', 'g值(1-X/2)'])
        
        csv_data.append(headers)
        
        # 数据行
        for item in stats_data:
            row = [item['name'], item['F'], item['V'], item['E']]
            if self.include_ratios:
                row.extend([f"{item['V/F']:.4f}", f"{item['E/F']:.4f}"])
            if self.include_formulas:
                row.extend([item['X'], f"{item['g']:.4f}"])
            csv_data.append(row)
        
        # 写入CSV文件（使用utf-8-sig编码确保Excel兼容性）
        try:
            with open(self.filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(csv_data)
            
            self.report({'INFO'}, f"导出成功: {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"导出失败: {str(e)}")
            return {'CANCELLED'}

class MESH_PT_stats_export_panel(Panel):
    """创建UI面板显示网格统计数据并导出"""
    bl_label = "网格统计导出器"
    bl_idname = "MESH_PT_stats_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh Stats"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 计算按钮
        row = layout.row()
        row.operator("mesh.calculate_multiple_stats", text="计算选中网格", icon='MODIFIER')
        
        # 分隔线
        layout.separator()
        
        # 显示选中对象数量
        selected_count = len([obj for obj in context.selected_objects if obj.type == 'MESH'])
        box = layout.box()
        box.label(text=f"选中网格对象: {selected_count}个", icon='OBJECT_DATA')
        
        # 分隔线
        layout.separator()
        
        # 导出选项
        box = layout.box()
        box.label(text="导出选项", icon='EXPORT')
        
        col = box.column(align=True)
        col.prop(context.scene, 'mesh_export_include_ratios', text="包含比值")
        col.prop(context.scene, 'mesh_export_include_formulas', text="包含公式计算")
        
        # 导出按钮
        row = layout.row()
        row.operator("mesh.export_stats_csv", text="导出为CSV", icon='FILE')
        
        # 分隔线
        layout.separator()
        
        # 显示最近计算的统计数据（如果有）
        if hasattr(scene, 'mesh_stats_data') and scene.mesh_stats_data:
            try:
                import ast
                stats_data = ast.literal_eval(scene.mesh_stats_data)
                
                box = layout.box()
                box.label(text="最近计算结果", icon='INFO')
                
                for i, item in enumerate(stats_data[:5]):  # 只显示前5个
                    col = box.column(align=True)
                    col.label(text=f"{item['name']}: F={item['F']}, V={item['V']}, E={item['E']}")
                
                if len(stats_data) > 5:
                    box.label(text=f"... 还有{len(stats_data)-5}个对象")
            except:
                pass

# 注册属性
def register():
    bpy.utils.register_class(MESH_OT_calculate_multiple_stats)
    bpy.utils.register_class(MESH_OT_export_stats_csv)
    bpy.utils.register_class(MESH_PT_stats_export_panel)
    
    # 注册场景属性
    bpy.types.Scene.mesh_stats_data = bpy.props.StringProperty(
        name="网格统计数据",
        default="",
        description="存储网格统计数据的JSON字符串"
    )
    
    bpy.types.Scene.mesh_export_include_ratios = bpy.props.BoolProperty(
        name="包含比值",
        description="导出时包含V/F和E/F比值",
        default=True
    )
    
    bpy.types.Scene.mesh_export_include_formulas = bpy.props.BoolProperty(
        name="包含公式计算",
        description="导出时包含X值和g值",
        default=True
    )

def unregister():
    bpy.utils.unregister_class(MESH_OT_calculate_multiple_stats)
    bpy.utils.unregister_class(MESH_OT_export_stats_csv)
    bpy.utils.unregister_class(MESH_PT_stats_export_panel)
    
    # 删除场景属性
    del bpy.types.Scene.mesh_stats_data
    del bpy.types.Scene.mesh_export_include_ratios
    del bpy.types.Scene.mesh_export_include_formulas

if __name__ == "__main__":
    register()