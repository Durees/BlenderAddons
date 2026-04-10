"""
批量独立Smart UV Project脚本
版本: 1.0
作者: 基于UV快速展开工具（增强版）
描述: 对选中的多个网格物体分别执行独立的Smart UV Project，每个物体都有自己的0-1 UV空间
"""

import bpy

def batch_smart_uv_project():
    """
    批量独立Smart UV Project主函数
    对当前选中的所有网格物体分别执行Smart UV Project
    """
    # 获取选中的网格物体
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("错误: 没有选中的网格物体")
        return
    
    # 保存原始状态
    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    original_selection = bpy.context.selected_objects.copy()
    
    success_count = 0
    failed_count = 0
    
    print(f"开始批量处理 {len(mesh_objects)} 个网格物体...")
    
    try:
        for i, obj in enumerate(mesh_objects):
            print(f"处理物体 {i+1}/{len(mesh_objects)}: {obj.name}")
            
            try:
                # 设置活动物体
                bpy.context.view_layer.objects.active = obj
                
                # 进入编辑模式
                bpy.ops.object.mode_set(mode='EDIT')
                
                # 选择所有面
                bpy.ops.mesh.select_all(action='SELECT')
                
                # 执行Smart UV Project
                # 参数匹配Blender UI中的默认设置
                bpy.ops.uv.smart_project(
                    angle_limit=66.0,           # 角度限制: 66度
                    margin_method='SCALED',     # 边距方法: 缩放
                    rotate_method='AXIS_ALIGNED_Y',  # 旋转方法: 轴对齐垂直
                    island_margin=0.0,          # 岛屿间距: 0.0
                    area_weight=0.0,            # 面积权重: 0.0
                    correct_aspect=True,        # 校正宽高比: True
                    scale_to_bounds=False       # 缩放到边界: False
                )
                
                # 返回物体模式
                bpy.ops.object.mode_set(mode='OBJECT')
                
                success_count += 1
                print(f"  ✓ 成功: {obj.name}")
                
            except Exception as e:
                failed_count += 1
                print(f"  ✗ 失败: {obj.name} - 错误: {e}")
                
                # 确保返回物体模式
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass
        
        # 恢复原始状态
        if original_active:
            bpy.context.view_layer.objects.active = original_active
        
        # 恢复原始选择
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            obj.select_set(True)
        
        # 恢复原始模式
        if original_mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass
        
        print(f"\n处理完成!")
        print(f"成功: {success_count} 个物体")
        if failed_count > 0:
            print(f"失败: {failed_count} 个物体")
        
    except Exception as e:
        print(f"批量处理过程中出错: {e}")
        
        # 尝试恢复原始状态
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            if original_active:
                bpy.context.view_layer.objects.active = original_active
        except:
            pass

# 清除所有选中物体的UVMap函数
def clear_all_uvmaps():
    """
    清除所有选中物体的UVMap
    """
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("错误: 没有选中的网格物体")
        return
    
    # 保存原始状态
    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    
    cleared_count = 0
    
    print(f"开始清除 {len(mesh_objects)} 个网格物体的UVMap...")
    
    try:
        for obj in mesh_objects:
            try:
                # 检查物体是否有UVMap
                if not obj.data.uv_layers:
                    continue
                
                # 设置活动物体
                bpy.context.view_layer.objects.active = obj
                
                # 进入编辑模式
                bpy.ops.object.mode_set(mode='EDIT')
                
                # 选择所有面
                bpy.ops.mesh.select_all(action='SELECT')
                
                # 清除UV（重置UV坐标）
                bpy.ops.uv.reset()
                
                # 返回物体模式
                bpy.ops.object.mode_set(mode='OBJECT')
                
                cleared_count += 1
                print(f"  ✓ 已清除: {obj.name}")
                
            except Exception as e:
                print(f"  ✗ 清除失败: {obj.name} - 错误: {e}")
                
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
        
        print(f"\n清除完成!")
        print(f"已清除 {cleared_count} 个物体的UVMap")
        
    except Exception as e:
        print(f"清除过程中出错: {e}")

# 主执行部分
if __name__ == "__main__":
    print("=" * 50)
    print("批量独立Smart UV Project脚本")
    print("=" * 50)
    print("\n功能:")
    print("1. 批量独立Smart UV Project")
    print("2. 清除所有选中物体的UVMap")
    print("\n使用方法:")
    print("1. 在3D视图中选中一个或多个网格物体")
    print("2. 运行以下函数之一:")
    print("   - batch_smart_uv_project(): 执行批量独立Smart UV Project")
    print("   - clear_all_uvmaps(): 清除所有选中物体的UVMap")
    print("\n开始执行批量独立Smart UV Project...")
    
    # 执行批量Smart UV Project
    batch_smart_uv_project()
    
    print("\n脚本执行完毕!")