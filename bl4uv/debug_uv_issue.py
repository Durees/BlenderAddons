"""
调试UV问题脚本
用于诊断为什么多物体的UV会被压缩到同一个0-1空间中
"""

import bpy

def debug_uv_issue():
    """调试UV问题"""
    print("=" * 60)
    print("开始调试UV问题")
    print("=" * 60)
    
    # 获取选中的网格物体
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("错误: 没有选中的网格物体")
        return
    
    print(f"选中的网格物体数量: {len(mesh_objects)}")
    
    # 检查每个物体的UV图层
    for i, obj in enumerate(mesh_objects):
        print(f"\n物体 {i+1}: {obj.name}")
        print(f"  UV图层数量: {len(obj.data.uv_layers)}")
        
        for j, uv_layer in enumerate(obj.data.uv_layers):
            print(f"  UV图层 {j}: {uv_layer.name} (活动: {uv_layer.active})")
    
    # 测试单独处理每个物体
    print("\n" + "=" * 60)
    print("测试单独处理每个物体")
    print("=" * 60)
    
    # 保存原始状态
    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    
    for i, obj in enumerate(mesh_objects):
        print(f"\n处理物体 {i+1}: {obj.name}")
        
        try:
            # 设置活动物体
            bpy.context.view_layer.objects.active = obj
            print(f"  设置活动物体: {obj.name}")
            
            # 进入编辑模式
            bpy.ops.object.mode_set(mode='EDIT')
            print(f"  进入编辑模式")
            
            # 选择所有面
            bpy.ops.mesh.select_all(action='SELECT')
            print(f"  选择所有面")
            
            # 检查当前UV图层
            mesh = obj.data
            if mesh.uv_layers:
                active_uv = mesh.uv_layers.active
                if active_uv:
                    print(f"  当前活动UV图层: {active_uv.name}")
            
            # 执行Smart UV Project
            print(f"  执行Smart UV Project")
            bpy.ops.uv.smart_project(
                angle_limit=66.0,
                margin_method='SCALED',
                rotate_method='AXIS_ALIGNED_Y',
                island_margin=0.0,
                area_weight=0.0,
                correct_aspect=True,
                scale_to_bounds=True  # 改为True确保填充0-1空间
            )
            
            # 返回物体模式
            bpy.ops.object.mode_set(mode='OBJECT')
            print(f"  返回物体模式 - 完成")
            
        except Exception as e:
            print(f"  处理失败: {e}")
            
            # 确保返回物体模式
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
    
    # 恢复原始状态
    if original_active:
        bpy.context.view_layer.objects.active = original_active
    if original_mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode=original_mode)
        except:
            pass
    
    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)

# 运行调试
if __name__ == "__main__":
    debug_uv_issue()