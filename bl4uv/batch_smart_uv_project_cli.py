#!/usr/bin/env python3
"""
批量Smart UV Project - 终端CLI版本
版本: 4.1
描述: 输入一个文件夹路径，读取里面的所有 .obj/.fbx 文件，
      对每个文件中的网格物体执行 Smart UV Project，
      然后在输入文件夹中创建 uv 子文件夹，把展开后的文件保存进去。

依赖: pip install bpy  (Blender Python绑定，可在系统Python中直接使用)

用法:
  python batch_smart_uv_project_cli.py
  python batch_smart_uv_project_cli.py /path/to/models
  python batch_smart_uv_project_cli.py /path/to/models --angle-limit 45 --island-margin 0.01
  python batch_smart_uv_project_cli.py /path/to/models --clear
  python batch_smart_uv_project_cli.py /path/to/models --action clear

  # 使用Blender内置Python运行（如果系统Python没有bpy）
  /Applications/Blender.app/Contents/MacOS/Blender --background --python batch_smart_uv_project_cli.py -- /path/to/models
"""

import argparse
import os
import sys
import glob
import json
import time


def import_bpy():
    """导入bpy，带友好的错误提示"""
    try:
        import bpy as _bpy
        # 验证bpy已完全初始化
        _ = _bpy.app.version_string
        return _bpy
    except ImportError:
        print("=" * 50)
        print("错误: 未安装 bpy 模块")
        print("=" * 50)
        print()
        print("当前Python:", sys.executable)
        print()
        print("方案1: 在当前Python环境中安装bpy")
        print("  pip install bpy")
        print()
        print("方案2: 使用Blender内置Python运行")
        print("  先找到Blender路径:")
        print("    /Applications/Blender.app/Contents/MacOS/Blender --background --python batch_smart_uv_project_cli.py -- /path/to/models")
        print()
        print("方案3: 使用conda环境（如果bpy安装在conda中）")
        print("  conda run -n your_env python batch_smart_uv_project_cli.py /path/to/models")
        print()
        sys.exit(1)
    except AttributeError as e:
        print(f"错误: bpy 模块未完全初始化: {e}")
        print("当前Python:", sys.executable)
        print("尝试重新安装: pip uninstall bpy -y && pip install bpy")
        sys.exit(1)


# 在模块级别尝试导入bpy（但允许失败，由main控制流程）
_bpy = None


def process_single_file(input_file, output_file, angle_limit, island_margin,
                        area_weight, clear_first, action):
    """处理单个文件：导入 -> UV操作 -> 导出"""
    global _bpy
    bpy = _bpy
    
    result = {
        "success": 0, "failed": 0, "errors": [],
        "input": input_file, "output": output_file
    }
    
    # 清除场景
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 导入文件
    ext = os.path.splitext(input_file)[1].lower()
    
    try:
        if ext == '.obj':
            bpy.ops.wm.obj_import(filepath=input_file)
        elif ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=input_file)
        else:
            bpy.ops.wm.obj_import(filepath=input_file)
    except Exception as e:
        result["errors"].append(f"导入失败: {e}")
        return result
    
    # 获取网格物体
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objects:
        result["errors"].append("文件中没有网格物体")
        return result
    
    # 取消所有选择
    bpy.ops.object.select_all(action='DESELECT')
    
    if action == "clear":
        # 仅清除UV
        for obj in mesh_objects:
            try:
                if not obj.data.uv_layers:
                    continue
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.reset()
                bpy.ops.object.mode_set(mode='OBJECT')
                obj.select_set(False)
                result["success"] += 1
            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{obj.name}: {e}")
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass
    else:
        # Smart UV Project
        for obj in mesh_objects:
            try:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                if clear_first and obj.data.uv_layers:
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.uv.reset()
                    bpy.ops.object.mode_set(mode='OBJECT')
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(
                    angle_limit=angle_limit,
                    margin_method='SCALED',
                    rotate_method='AXIS_ALIGNED_Y',
                    island_margin=island_margin,
                    area_weight=area_weight,
                    correct_aspect=True,
                    scale_to_bounds=False
                )
                bpy.ops.object.mode_set(mode='OBJECT')
                obj.select_set(False)
                result["success"] += 1
            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{obj.name}: {e}")
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass
    
    # 导出
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)
    
    out_ext = os.path.splitext(output_file)[1].lower()
    try:
        if out_ext == '.obj':
            bpy.ops.wm.obj_export(
                filepath=output_file,
                export_selected_objects=True,
                apply_modifiers=False,
                export_uv=True,
                export_normals=True,
                export_materials=True,
                export_colors=False,
                global_scale=1.0,
                forward_axis='NEGATIVE_Z',
                up_axis='Y',
                export_triangulated_mesh=False,
                export_vertex_groups=False,
                export_smooth_groups=True,
            )
        elif out_ext == '.fbx':
            bpy.ops.export_scene.fbx(
                filepath=output_file,
                use_selection=True,
                apply_scale_options='FBX_SCALE_UNITS',
                object_types={'MESH'}
            )
    except Exception as e:
        result["errors"].append(f"导出失败: {e}")
    
    return result


def process_folder(input_dir, **kwargs):
    """处理文件夹中的所有.obj/.fbx文件"""
    global _bpy
    
    input_dir = os.path.abspath(input_dir)
    
    if not os.path.isdir(input_dir):
        print(f"错误: 文件夹不存在: {input_dir}")
        return False
    
    # 收集所有支持的模型文件
    model_files = []
    for ext in ("*.obj", "*.OBJ", "*.fbx", "*.FBX"):
        model_files.extend(glob.glob(os.path.join(input_dir, ext)))
    
    if not model_files:
        print(f"错误: 文件夹中没有找到 .obj 或 .fbx 文件: {input_dir}")
        return False
    
    model_files.sort()
    print(f"\n找到 {len(model_files)} 个模型文件")
    
    # 创建 uv 输出文件夹
    output_dir = os.path.join(input_dir, "uv")
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出文件夹: {output_dir}")
    
    # 导入bpy
    print("\n正在初始化 Blender Python 环境...")
    t_start = time.time()
    _bpy = import_bpy()
    print(f"  Blender {_bpy.app.version_string} 已就绪 ({time.time()-t_start:.1f}s)")
    
    # 参数
    angle_limit = kwargs.get("angle_limit", 66.0)
    island_margin = kwargs.get("island_margin", 0.0)
    area_weight = kwargs.get("area_weight", 0.0)
    clear_first = kwargs.get("clear", False)
    action = kwargs.get("action", "unwrap")
    
    # 逐个处理
    total_success = 0
    total_failed = 0
    all_results = []
    
    for i, file_path in enumerate(model_files):
        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)
        
        print(f"\n[{i+1}/{len(model_files)}] {filename}")
        print("-" * 40)
        
        t_file = time.time()
        result = process_single_file(
            file_path, output_path,
            angle_limit, island_margin, area_weight,
            clear_first, action
        )
        elapsed = time.time() - t_file
        
        all_results.append(result)
        total_success += result["success"]
        total_failed += result["failed"]
        
        s = result["success"]
        f = result["failed"]
        if f == 0 and s > 0:
            print(f"  ✓ 完成 ({elapsed:.1f}s)")
        elif f > 0:
            print(f"  ⚠ 部分完成 成功:{s} 失败:{f} ({elapsed:.1f}s)")
        else:
            print(f"  ✗ 失败 ({elapsed:.1f}s)")
        
        for err in result.get("errors", []):
            print(f"    错误: {err}")
    
    # 汇总
    print(f"\n{'='*50}")
    print(f"全部处理完成!")
    print(f"  处理文件数: {len(model_files)}")
    print(f"  成功物体数: {total_success}")
    print(f"  失败物体数: {total_failed}")
    print(f"  输出目录: {output_dir}")
    
    return total_failed == 0


def main():
    # 检查是否在Blender环境中运行（通过 -- 分隔符）
    if "--" in sys.argv:
        # Blender模式：sys.argv 在 -- 之后的是实际参数
        idx = sys.argv.index("--")
        blender_args = sys.argv[idx + 1:]
        # 只保留脚本参数，去掉Blender自身的参数
        sys.argv = [sys.argv[0]] + blender_args
    
    parser = argparse.ArgumentParser(
        description="批量Smart UV Project - 终端CLI版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 交互式询问路径
  %(prog)s /path/to/models              # 直接指定路径
  %(prog)s /path/to/models --angle-limit 45 --island-margin 0.01
  %(prog)s /path/to/models --clear      # 展开前清除UV
  %(prog)s /path/to/models --action clear  # 仅清除UV

  # Blender内置Python运行:
  blender --background --python %(prog)s -- /path/to/models
        """
    )
    
    parser.add_argument(
        "input_dir", nargs="?", default=None,
        help="输入文件夹路径（不提供则交互式询问）"
    )
    parser.add_argument(
        "--action", choices=["unwrap", "clear"], default="unwrap",
        help="操作类型: unwrap(展开UV) 或 clear(清除UV) (默认: unwrap)"
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="展开前先清除现有UV"
    )
    parser.add_argument(
        "--angle-limit", type=float, default=66.0,
        help="角度限制，单位度 (默认: 66)"
    )
    parser.add_argument(
        "--island-margin", type=float, default=0.0,
        help="UV岛屿间距 (默认: 0.0)"
    )
    parser.add_argument(
        "--area-weight", type=float, default=0.0,
        help="面积权重 (默认: 0.0)"
    )
    
    args = parser.parse_args()
    
    # 交互式询问路径
    if not args.input_dir:
        print("=" * 50)
        print("批量 Smart UV Project - 终端工具")
        print("=" * 50)
        args.input_dir = input("\n请输入包含 .obj/.fbx 文件的文件夹路径: ").strip()
        args.input_dir = args.input_dir.strip("'\" ")
        args.input_dir = os.path.expanduser(args.input_dir)
        
        if not args.input_dir:
            print("错误: 未输入文件夹路径")
            sys.exit(1)
        print()
    
    # 处理文件夹
    success = process_folder(
        args.input_dir,
        action=args.action,
        clear=args.clear,
        angle_limit=args.angle_limit,
        island_margin=args.island_margin,
        area_weight=args.area_weight
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
