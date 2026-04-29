"""
Blender 自动化减面处理脚本 (双模式)
====================================
功能：遍历目标文件夹中的 Mesh 文件，应用减面算法进行处理，
      并将优化后的文件导出到指定目录。

运行模式：
  [模式 A] Blender 环境 — 使用 bpy 的 Decimate (Collapse) 修改器
  [模式 B] 普通 Python 环境 — 使用 trimesh 库的简化算法

依赖安装（普通 Python 环境）：
  pip install trimesh numpy fast_simplification

兼容性：Blender 3.x / 4.x, Python 3.8+
"""

import os
import sys
import traceback

# ============================================================
# 用户配置区（也可通过交互式输入覆盖）
# ============================================================
INPUT_DIR = ""          # 输入文件夹路径（留空则通过 input() 询问）
OUTPUT_DIR = ""         # 输出文件夹路径（留空则通过 input() 询问）
RATIO = 0.0             # 塌陷比率 (0.0 ~ 1.0)，留空则通过 input() 询问
OUTPUT_FORMAT = ""      # 输出格式（留空则通过 input() 询问，可选值见下方 SUPPORTED_EXTENSIONS）

# 支持的格式列表
# key: 文件扩展名, value: (格式名称, 格式描述)
SUPPORTED_EXTENSIONS = {
    '.obj':  ('OBJ',  'Wavefront OBJ (通用格式)'),
    '.stl':  ('STL',  'STereoLithography (3D打印)'),
    '.fbx':  ('FBX',  'Filmbox (通用交换格式)'),
    '.glb':  ('GLB',  'GLTF Binary (Web/游戏)'),
    '.gltf': ('GLTF', 'GLTF Text (Web/游戏)'),
    '.ply':  ('PLY',  'Polygon File Format (点云/扫描)'),
    '.x3d':  ('X3D',  'X3D (Web3D/VR)'),
}

# 导出后缀（设为空字符串则直接覆盖原文件名，注意不要和输入目录相同）
SUFFIX = ""


# ============================================================
# 环境检测与模式选择
# ============================================================

def detect_engine():
    """
    检测可用的减面引擎。
    返回: 'blender' 或 'trimesh' 或 None
    """
    # 先尝试 Blender 的 bpy
    try:
        import bpy
        if hasattr(bpy, 'context') and hasattr(bpy, 'data') and hasattr(bpy, 'ops'):
            return 'blender'
    except ImportError:
        pass

    # 再尝试 trimesh
    try:
        import trimesh
        return 'trimesh'
    except ImportError:
        pass

    return None


def print_engine_info(engine):
    """打印引擎信息"""
    if engine == 'blender':
        import bpy
        print(f"[信息] 减面引擎: Blender bpy (v{bpy.app.version_string})")
    elif engine == 'trimesh':
        import trimesh
        print(f"[信息] 减面引擎: trimesh (v{trimesh.__version__})")


def print_no_engine_guide():
    """当没有可用引擎时打印指引"""
    print("=" * 60)
    print("  [错误] 未找到可用的减面引擎")
    print("  " + "-" * 56)
    print("  请选择以下方式之一：")
    print()
    print("  方式 1: 使用 Blender（推荐）")
    print("     blender --background --python decimate_batch.py")
    print()
    print("  方式 2: 安装 trimesh（普通 Python 环境）")
    print("     pip install trimesh numpy")
    print("     python decimate_batch.py")
    print("=" * 60)


# ============================================================
# 模式 A: Blender bpy 引擎
# ============================================================

def get_import_export_funcs():
    """
    根据 Blender 版本返回对应的导入/导出函数映射。
    Blender 4.x 开始将部分导入算子迁移到 bpy.ops.wm.* 命名空间。
    """
    import bpy

    version = bpy.app.version
    major = version[0]

    # 默认映射（Blender 3.x 及以下）
    import_map = {
        'OBJ':  bpy.ops.import_scene.obj,
        'STL':  bpy.ops.import_mesh.stl,
        'FBX':  bpy.ops.import_scene.fbx,
        'GLB':  bpy.ops.import_scene.gltf,
        'GLTF': bpy.ops.import_scene.gltf,
        'PLY':  bpy.ops.import_mesh.ply,
        'X3D':  bpy.ops.import_scene.x3d,
    }
    export_map = {
        'OBJ':  bpy.ops.export_scene.obj,
        'STL':  bpy.ops.export_mesh.stl,
        'FBX':  bpy.ops.export_scene.fbx,
        'GLB':  bpy.ops.export_scene.gltf,
        'GLTF': bpy.ops.export_scene.gltf,
        'PLY':  bpy.ops.export_mesh.ply,
        'X3D':  bpy.ops.export_scene.x3d,
    }

    # Blender 4.x 调整
    if major >= 4:
        import_map['OBJ'] = bpy.ops.wm.obj_import
        import_map['STL'] = bpy.ops.wm.stl_import
        import_map['PLY'] = bpy.ops.wm.ply_import

        export_map['OBJ'] = bpy.ops.wm.obj_export
        export_map['STL'] = bpy.ops.wm.stl_export
        export_map['PLY'] = bpy.ops.wm.ply_export

    return import_map, export_map


def blender_reset_scene():
    """重置 Blender 场景：删除所有对象并清理 orphan 数据块。"""
    import bpy

    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.data.orphans_purge()


def blender_import_model(filepath):
    """使用 Blender 导入模型，返回新增对象列表。"""
    import bpy

    ext = os.path.splitext(filepath)[1].lower()
    fmt_info = SUPPORTED_EXTENSIONS.get(ext)
    if fmt_info is None:
        raise ValueError(f"不支持的格式: {ext}")
    fmt = fmt_info[0]

    import_map, _ = get_import_export_funcs()
    importer = import_map.get(fmt)
    if importer is None:
        raise ValueError(f"未找到 {fmt} 的导入函数")

    old_objects = set(bpy.data.objects)
    importer(filepath=filepath)
    new_objects = [obj for obj in bpy.data.objects if obj not in old_objects]

    return new_objects


def blender_apply_decimate(objects, ratio):
    """使用 Blender Decimate (Collapse) 修改器减面。"""
    import bpy

    if not objects:
        print("  [警告] 没有可处理的对象")
        return None

    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)

    if len(objects) > 1:
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        merged_obj = bpy.context.active_object
        print(f"  [信息] 合并了 {len(objects)} 个对象为: {merged_obj.name}")
    else:
        merged_obj = objects[0]
        bpy.context.view_layer.objects.active = merged_obj

    modifier = merged_obj.modifiers.new(name="Decimate", type='DECIMATE')
    modifier.decimate_type = 'COLLAPSE'
    modifier.ratio = ratio

    bpy.ops.object.modifier_apply(modifier=modifier.name)

    print(f"  [信息] 已应用 Decimate (Collapse), 比率={ratio:.4f}")
    return merged_obj


def blender_export_model(obj, output_path, target_ext):
    """使用 Blender 导出模型。"""
    import bpy

    ext = target_ext.lower()
    fmt_info = SUPPORTED_EXTENSIONS.get(ext)
    if fmt_info is None:
        raise ValueError(f"不支持的格式: {ext}")
    fmt = fmt_info[0]

    _, export_map = get_import_export_funcs()
    exporter = export_map.get(fmt)
    if exporter is None:
        raise ValueError(f"未找到 {fmt} 的导出函数")

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    exporter(filepath=output_path, use_selection=True)

    print(f"  [完成] 已导出: {output_path}")


# ============================================================
# 模式 B: trimesh 引擎
# ============================================================

def trimesh_load_model(filepath):
    """使用 trimesh 加载模型。"""
    import trimesh

    mesh = trimesh.load(filepath)
    # 如果场景包含多个 mesh，合并为一个
    if isinstance(mesh, trimesh.Scene):
        print(f"  [信息] 场景包含多个 mesh，正在合并...")
        mesh = trimesh.util.concatenate(
            [geometry for geometry in mesh.geometry.values()
             if isinstance(geometry, trimesh.Trimesh)]
        )
    return mesh


def trimesh_apply_decimate(mesh, ratio):
    """
    使用 trimesh 的简化算法进行减面。
    优先使用 fast_simplification（性能更好），
    回退使用 trimesh 内置的 simplify_quadric_decimation。
    """
    import trimesh

    if mesh is None:
        print("  [警告] 没有可处理的 mesh")
        return None

    if not isinstance(mesh, trimesh.Trimesh):
        print("  [错误] 不支持的 mesh 类型")
        return None

    # 计算目标面数
    current_faces = len(mesh.faces)
    target_faces = max(1, int(current_faces * ratio))

    print(f"  [信息] 当前面数: {current_faces}, 目标面数: {target_faces}")

    if target_faces >= current_faces:
        print(f"  [信息] 目标面数 >= 当前面数，无需减面")
        return mesh

    # 方案 1: 使用 fast_simplification（性能最好）
    try:
        from fast_simplification import simplify
        import numpy as np

        vertices = np.array(mesh.vertices, dtype=np.float64)
        faces = np.array(mesh.faces, dtype=np.int32)

        # target_reduction: 0.0 = 不简化, 1.0 = 完全简化
        # 我们想保留 ratio 的面数，所以 reduction = 1.0 - ratio
        simplified_verts, simplified_faces = simplify(
            vertices, faces, target_reduction=1.0 - ratio
        )

        simplified = trimesh.Trimesh(
            vertices=simplified_verts,
            faces=simplified_faces,
        )
        actual_faces = len(simplified.faces)
        print(f"  [信息] 已简化 (fast_simplification): {current_faces} -> {actual_faces} 面")
        return simplified

    except ImportError:
        print("  [信息] fast_simplification 未安装，使用 trimesh 内置简化")
        print("  [信息] 如需更好性能: pip install fast_simplification")

    # 方案 2: 使用 trimesh 内置的 simplify_quadric_decimation
    try:
        simplified = mesh.simplify_quadric_decimation(target_faces)
        actual_faces = len(simplified.faces)
        print(f"  [信息] 已简化 (trimesh): {current_faces} -> {actual_faces} 面")
        return simplified

    except ImportError:
        print("  [错误] 无法简化 mesh — 缺少必要的简化库")
        print("  [建议] pip install fast_simplification")
        return mesh


def trimesh_export_model(mesh, output_path, target_ext):
    """使用 trimesh 导出模型。"""
    import trimesh

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    ext = target_ext.lower()
    if ext == '.glb':
        # GLB 需要特殊处理
        scene = trimesh.Scene([mesh])
        scene.export(output_path, file_type='glb')
    elif ext == '.gltf':
        scene = trimesh.Scene([mesh])
        scene.export(output_path, file_type='gltf')
    elif ext == '.x3d':
        scene = trimesh.Scene([mesh])
        scene.export(output_path, file_type='x3d')
    else:
        mesh.export(output_path)

    print(f"  [完成] 已导出: {output_path}")


# ============================================================
# 统一的处理流水线
# ============================================================

def process_file_blender(filepath, output_dir, ratio, output_ext):
    """Blender 模式：处理单个文件。"""
    import bpy

    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]

    print(f"\n{'='*60}")
    print(f"[处理] {filename}")
    print(f"{'='*60}")

    try:
        blender_reset_scene()

        print(f"  [导入] {filepath}")
        imported_objects = blender_import_model(filepath)
        if not imported_objects:
            print(f"  [错误] 导入后未检测到任何对象: {filename}")
            return False
        print(f"  [信息] 导入了 {len(imported_objects)} 个对象")

        processed_obj = blender_apply_decimate(imported_objects, ratio)
        if processed_obj is None:
            return False

        output_filename = f"{name_no_ext}{SUFFIX}{output_ext}"
        output_path = os.path.join(output_dir, output_filename)
        blender_export_model(processed_obj, output_path, output_ext)

        return True

    except Exception as e:
        print(f"  [错误] 处理文件时出错: {filename}")
        print(f"  [错误] {e}")
        traceback.print_exc()
        return False


def process_file_trimesh(filepath, output_dir, ratio, output_ext):
    """trimesh 模式：处理单个文件。"""
    import trimesh

    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]

    print(f"\n{'='*60}")
    print(f"[处理] {filename}")
    print(f"{'='*60}")

    try:
        print(f"  [加载] {filepath}")
        mesh = trimesh_load_model(filepath)
        if mesh is None:
            print(f"  [错误] 无法加载模型: {filename}")
            return False

        if isinstance(mesh, trimesh.Trimesh):
            print(f"  [信息] 顶点数: {len(mesh.vertices)}, 面数: {len(mesh.faces)}")
        else:
            print(f"  [信息] 模型类型: {type(mesh).__name__}")

        processed_mesh = trimesh_apply_decimate(mesh, ratio)
        if processed_mesh is None:
            return False

        output_filename = f"{name_no_ext}{SUFFIX}{output_ext}"
        output_path = os.path.join(output_dir, output_filename)
        trimesh_export_model(processed_mesh, output_path, output_ext)

        return True

    except Exception as e:
        print(f"  [错误] 处理文件时出错: {filename}")
        print(f"  [错误] {e}")
        traceback.print_exc()
        return False


def batch_process(input_dir, output_dir, ratio, output_ext, engine):
    """
    批量处理文件夹中的所有支持文件。
    engine: 'blender' 或 'trimesh'
    """
    # 收集所有支持的文件
    files_to_process = []
    for filename in os.listdir(input_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filepath = os.path.join(input_dir, filename)
            if os.path.isfile(filepath):
                files_to_process.append(filepath)

    files_to_process.sort()

    total = len(files_to_process)
    if total == 0:
        print(f"\n[信息] 在目录中未找到支持的模型文件: {input_dir}")
        print(f"[信息] 支持的格式: {', '.join(SUPPORTED_EXTENSIONS.keys())}")
        return

    fmt_info = SUPPORTED_EXTENSIONS.get(output_ext, ('未知', ''))
    output_fmt_name = fmt_info[0]

    print(f"\n{'#'*60}")
    print(f"# 批量减面处理开始")
    print(f"# 输入目录: {input_dir}")
    print(f"# 输出目录: {output_dir}")
    print(f"# 塌陷比率: {ratio:.4f}")
    print(f"# 输出格式: {output_fmt_name} ({output_ext})")
    print(f"# 文件数量: {total}")
    print(f"{'#'*60}\n")

    # 选择处理函数
    if engine == 'blender':
        process_func = process_file_blender
    else:
        process_func = process_file_trimesh

    success_count = 0
    fail_count = 0

    for idx, filepath in enumerate(files_to_process, 1):
        filename = os.path.basename(filepath)
        print(f"\n>>> 进度: [{idx}/{total}] 剩余: {total - idx}")

        success = process_func(filepath, output_dir, ratio, output_ext)
        if success:
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'#'*60}")
    print(f"# 批量处理完成")
    print(f"# 成功: {success_count}")
    print(f"# 失败: {fail_count}")
    print(f"# 总计: {total}")
    print(f"{'#'*60}")


# ============================================================
# 交互式输入
# ============================================================

def get_user_input():
    """
    获取用户输入（路径和参数）。
    如果已在脚本顶部配置了值，则跳过对应的询问。
    """
    global INPUT_DIR, OUTPUT_DIR, RATIO, OUTPUT_FORMAT

    print("=" * 60)
    print("  自动化减面处理工具")
    print("=" * 60)

    # 输入目录
    if not INPUT_DIR:
        INPUT_DIR = input("\n请输入输入文件夹路径 (待处理的模型文件): ").strip()
        if not INPUT_DIR:
            print("[错误] 输入路径不能为空")
            sys.exit(1)

    if not os.path.isdir(INPUT_DIR):
        print(f"[错误] 输入目录不存在: {INPUT_DIR}")
        sys.exit(1)

    # 输出目录
    if not OUTPUT_DIR:
        OUTPUT_DIR = input("请输入输出文件夹路径 (处理后文件的保存位置): ").strip()
        if not OUTPUT_DIR:
            print("[错误] 输出路径不能为空")
            sys.exit(1)

    # 塌陷比率
    if RATIO <= 0.0 or RATIO > 1.0:
        while True:
            try:
                ratio_input = input("请输入塌陷比率 (0.0 ~ 1.0, 例如 0.5 表示减掉 50% 的面数): ").strip()
                RATIO = float(ratio_input)
                if 0.0 < RATIO <= 1.0:
                    break
                else:
                    print("[错误] 比率必须在 0.0 到 1.0 之间")
            except ValueError:
                print("[错误] 请输入有效的数字")

    # 输出格式选择
    if not OUTPUT_FORMAT:
        print("\n请选择输出格式:")
        format_list = list(SUPPORTED_EXTENSIONS.items())
        for i, (ext, (name, desc)) in enumerate(format_list, 1):
            print(f"  [{i}] {name:6s} ({ext}) — {desc}")
        print(f"  [0] 保持原格式（不转换）")

        while True:
            try:
                fmt_choice = input(f"\n请选择输出格式 [0-{len(format_list)}] (默认 0): ").strip()
                if not fmt_choice or fmt_choice == "0":
                    OUTPUT_FORMAT = ""
                    break
                idx = int(fmt_choice)
                if 1 <= idx <= len(format_list):
                    OUTPUT_FORMAT = format_list[idx - 1][0]
                    break
                else:
                    print(f"[错误] 请输入 0 到 {len(format_list)} 之间的数字")
            except ValueError:
                print("[错误] 请输入有效的数字")

    return INPUT_DIR, OUTPUT_DIR, RATIO, OUTPUT_FORMAT


# ============================================================
# 主入口
# ============================================================

def main():
    """主函数：检测引擎、获取参数、执行批量处理。"""
    # 1. 检测可用的减面引擎
    engine = detect_engine()
    if engine is None:
        print_no_engine_guide()
        sys.exit(1)

    print_engine_info(engine)

    # 2. 获取用户输入
    input_dir, output_dir, ratio, output_format = get_user_input()

    # 3. 执行批量处理
    if output_format:
        batch_process(input_dir, output_dir, ratio, output_format, engine)
    else:
        # 保持原格式
        files_to_process = []
        for filename in os.listdir(input_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                filepath = os.path.join(input_dir, filename)
                if os.path.isfile(filepath):
                    files_to_process.append((filepath, ext))

        files_to_process.sort(key=lambda x: x[0])

        total = len(files_to_process)
        if total == 0:
            print(f"\n[信息] 在目录中未找到支持的模型文件: {input_dir}")
            print(f"[信息] 支持的格式: {', '.join(SUPPORTED_EXTENSIONS.keys())}")
            return

        print(f"\n{'#'*60}")
        print(f"# 批量减面处理开始")
        print(f"# 输入目录: {input_dir}")
        print(f"# 输出目录: {output_dir}")
        print(f"# 塌陷比率: {ratio:.4f}")
        print(f"# 输出格式: 保持原格式")
        print(f"# 文件数量: {total}")
        print(f"{'#'*60}\n")

        if engine == 'blender':
            process_func = process_file_blender
        else:
            process_func = process_file_trimesh

        success_count = 0
        fail_count = 0

        for idx, (filepath, orig_ext) in enumerate(files_to_process, 1):
            filename = os.path.basename(filepath)
            print(f"\n>>> 进度: [{idx}/{total}] 剩余: {total - idx}")

            success = process_func(filepath, output_dir, ratio, orig_ext)
            if success:
                success_count += 1
            else:
                fail_count += 1

        print(f"\n{'#'*60}")
        print(f"# 批量处理完成")
        print(f"# 成功: {success_count}")
        print(f"# 失败: {fail_count}")
        print(f"# 总计: {total}")
        print(f"{'#'*60}")


if __name__ == "__main__":
    main()
