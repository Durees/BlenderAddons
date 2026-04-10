bl_info = {
    "name": "网格统计计算器",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Mesh Stats",
    "description": "计算选中网格的面数(F)、顶点数(V)、边数(E)及相关比值",
    "category": "Mesh",
}

import bpy
from bpy.types import Panel, Operator
from bpy.props import FloatProperty

class MESH_OT_calculate_stats(Operator):
    """计算选中网格的统计数据"""
    bl_idname = "mesh.calculate_stats"
    bl_label = "计算网格统计"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取选中的对象
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请选择一个网格对象")
            return {'CANCELLED'}
        
        mesh = obj.data
        
        # 计算基本统计数据
        F = len(mesh.polygons)  # 面数
        V = len(mesh.vertices)  # 顶点数
        E = len(mesh.edges)     # 边数
        
        # 存储到场景属性中
        scene = context.scene
        scene.mesh_stats_faces = F
        scene.mesh_stats_vertices = V
        scene.mesh_stats_edges = E
        
        # 计算比值
        if F > 0:
            scene.mesh_stats_vf_ratio = V / F
            scene.mesh_stats_ef_ratio = E / F
        else:
            scene.mesh_stats_vf_ratio = 0.0
            scene.mesh_stats_ef_ratio = 0.0
        
        # 计算X = V - E + F
        X = V - E + F
        scene.mesh_stats_x_value = X
        
        # 计算g = 1 - X/2
        g = 1 - X / 2
        scene.mesh_stats_g_value = g
        
        self.report({'INFO'}, f"计算完成: F={F}, V={V}, E={E}")
        return {'FINISHED'}

class MESH_PT_stats_panel(Panel):
    """创建UI面板显示网格统计数据"""
    bl_label = "网格统计计算器"
    bl_idname = "MESH_PT_stats_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh Stats"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 计算按钮
        row = layout.row()
        row.operator("mesh.calculate_stats", text="计算选中网格")
        
        # 分隔线
        layout.separator()
        
        # 基本统计数据
        box = layout.box()
        box.label(text="基本统计数据", icon='MESH_DATA')
        
        col = box.column(align=True)
        col.label(text=f"面数 (F): {scene.mesh_stats_faces}")
        col.label(text=f"顶点数 (V): {scene.mesh_stats_vertices}")
        col.label(text=f"边数 (E): {scene.mesh_stats_edges}")
        
        # 分隔线
        layout.separator()
        
        # 比值计算
        box = layout.box()
        box.label(text="比值计算", icon='MOD_DECIM')
        
        col = box.column(align=True)
        col.label(text=f"V/F 比值: {scene.mesh_stats_vf_ratio:.4f}")
        col.label(text=f"E/F 比值: {scene.mesh_stats_ef_ratio:.4f}")
        
        # 分隔线
        layout.separator()
        
        # 欧拉公式计算
        box = layout.box()
        box.label(text="欧拉公式计算", icon='CON_TRACKTO')
        
        col = box.column(align=True)
        col.label(text=f"X = V - E + F: {scene.mesh_stats_x_value}")
        col.label(text=f"g = 1 - X/2: {scene.mesh_stats_g_value:.4f}")
        
        # 解释说明
        layout.separator()
        box = layout.box()
        box.label(text="说明", icon='INFO')
        box.label(text="F: 面数 (多边形数量)")
        box.label(text="V: 顶点数 (顶点数量)")
        box.label(text="E: 边数 (边数量)")
        box.label(text="g: 亏格 (拓扑学中的曲面类型)")

# 注册属性
def register():
    bpy.utils.register_class(MESH_OT_calculate_stats)
    bpy.utils.register_class(MESH_PT_stats_panel)
    
    # 注册场景属性
    bpy.types.Scene.mesh_stats_faces = bpy.props.IntProperty(
        name="面数",
        default=0,
        description="网格的面数 (F)"
    )
    bpy.types.Scene.mesh_stats_vertices = bpy.props.IntProperty(
        name="顶点数",
        default=0,
        description="网格的顶点数 (V)"
    )
    bpy.types.Scene.mesh_stats_edges = bpy.props.IntProperty(
        name="边数",
        default=0,
        description="网格的边数 (E)"
    )
    bpy.types.Scene.mesh_stats_vf_ratio = bpy.props.FloatProperty(
        name="V/F比值",
        default=0.0,
        description="顶点数与面数的比值"
    )
    bpy.types.Scene.mesh_stats_ef_ratio = bpy.props.FloatProperty(
        name="E/F比值",
        default=0.0,
        description="边数与面数的比值"
    )
    bpy.types.Scene.mesh_stats_x_value = bpy.props.IntProperty(
        name="X值",
        default=0,
        description="X = V - E + F"
    )
    bpy.types.Scene.mesh_stats_g_value = bpy.props.FloatProperty(
        name="g值",
        default=0.0,
        description="g = 1 - X/2"
    )

def unregister():
    bpy.utils.unregister_class(MESH_OT_calculate_stats)
    bpy.utils.unregister_class(MESH_PT_stats_panel)
    
    # 删除场景属性
    del bpy.types.Scene.mesh_stats_faces
    del bpy.types.Scene.mesh_stats_vertices
    del bpy.types.Scene.mesh_stats_edges
    del bpy.types.Scene.mesh_stats_vf_ratio
    del bpy.types.Scene.mesh_stats_ef_ratio
    del bpy.types.Scene.mesh_stats_x_value
    del bpy.types.Scene.mesh_stats_g_value

if __name__ == "__main__":
    register()