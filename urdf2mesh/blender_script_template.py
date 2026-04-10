import bpy
import os
import traceback
import time
import json
from datetime import datetime

# 配置
input_folder = r'{input_folder}'
output_folder = r'{output_folder}'
checkpoint_file = os.path.join(output_folder, '.processing_checkpoint.json')
# UV投影参数（与官方API完全一致）
uv_angle_limit = {uv_angle_limit}          # Angle Limit（角度）
uv_island_margin = {uv_island_margin}      # Island Margin
uv_area_weight = {uv_area_weight}          # Area Weight
uv_correct_aspect = {uv_correct_aspect}    # Correct Aspect
uv_scale_to_bounds = {uv_scale_to_bounds}  # Scale to Bounds

def load_checkpoint():
    """加载检查点"""
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"processed_files": [], "start_time": time.time()}

def save_checkpoint(processed_files):
    """保存检查点"""
    checkpoint_data = {
        "processed_files": processed_files,
        "timestamp": datetime.now().isoformat(),
        "total_files": len(processed_files)
    }
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    except:
        pass

def estimate_remaining_time(start_time, current, total):
    """估算剩余时间"""
    if current == 0:
        return "计算中..."
    
    elapsed = time.time() - start_time
    time_per_file = elapsed / current
    remaining = time_per_file * (total - current)
    
    if remaining < 60:
        return f"{remaining:.0f}秒"
    elif remaining < 3600:
        return f"{remaining/60:.1f}分钟"
    else:
        return f"{remaining/3600:.1f}小时"

def run_process():
    """主处理函数"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取所有OBJ文件
    all_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".obj")]
    
    if not all_files:
        print("在输入文件夹中未找到OBJ文件。")
        return

    # 加载检查点
    checkpoint = load_checkpoint()
    processed_files = set(checkpoint.get("processed_files", []))
    
    # 过滤已处理的文件
    files_to_process = [f for f in all_files if f not in processed_files]
    
    if not files_to_process:
        print("所有文件已处理完成。")
        return
    
    total_files = len(files_to_process)
    print(f"找到 {len(all_files)} 个OBJ文件，其中 {total_files} 个需要处理。")
    
    if processed_files:
        print(f"已跳过 {len(processed_files)} 个已处理文件。")
    
    start_time = time.time()
    
    for i, file in enumerate(files_to_process, 1):
        try:
            # 显示进度
            progress = f"[{i}/{total_files}]"
            remaining = estimate_remaining_time(start_time, i-1, total_files)
            print(f"\n{progress} 处理: {file} (剩余: {remaining})")
            
            # 清理场景
            bpy.ops.wm.read_factory_settings(use_empty=True) 
            
            # 导入
            file_path = os.path.join(input_folder, file)
            bpy.ops.wm.obj_import(filepath=file_path)
            
            # 处理网格对象
            mesh_count = 0
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH':
                    mesh_count += 1
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    # smart UV投影
                    bpy.ops.uv.smart_project(
                        angle_limit=uv_angle_limit * 3.141592653589793 / 180.0,  # 角度转弧度
                        margin_method='SCALED',              # 默认值
                        rotate_method='AXIS_ALIGNED_Y',      # 默认值
                        island_margin=uv_island_margin,      # Island Margin
                        area_weight=uv_area_weight,          # Area Weight
                        correct_aspect=uv_correct_aspect,    # Correct Aspect
                        scale_to_bounds=uv_scale_to_bounds   # Scale to Bounds
                    )
                    bpy.ops.object.mode_set(mode='OBJECT')
            
            # 导出
            output_path = os.path.join(output_folder, file)
            bpy.ops.wm.obj_export(
                filepath=output_path, 
                export_selected_objects=True
            )
            
            # 更新已处理文件列表
            processed_files.add(file)
            
            # 每处理10个文件保存一次检查点
            if i % 10 == 0 or i == total_files:
                save_checkpoint(list(processed_files))
                print(f"  检查点已保存 ({i}/{total_files})")
            
            print(f"  完成: {file} (处理了{mesh_count}个网格对象)")
            
        except Exception as e:
            print(f"  处理 {file} 时出错: {e}")
            traceback.print_exc()
            continue
    
    # 处理完成
    elapsed_time = time.time() - start_time
    print(f"\n处理完成!")
    print(f"总文件数: {len(all_files)}")
    print(f"成功处理: {len(processed_files)}")
    print(f"失败文件: {len(all_files) - len(processed_files)}")
    print(f"总耗时: {elapsed_time:.1f}秒 ({elapsed_time/60:.1f}分钟)")
    
    # 清理检查点文件
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("检查点文件已清理。")

if __name__ == "__main__":
    run_process()