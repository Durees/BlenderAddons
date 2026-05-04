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
from typing import Optional, List, Tuple, Dict, Any, Union


# ============================================================
# 用户配置区（也可通过交互式输入覆盖）
# ============================================================
INPUT_DIR: str = ""          # 输入文件夹路径（留空则通过 input() 询问）
OUTPUT_DIR: str = ""         # 输出文件夹路径（留空则通过 input() 询问）
RATIO: float = 0.0           # 塌陷比率 (0.0 ~ 1.0)，留空则通过 input() 询问
OUTPUT_FORMAT: str = ""      # 输出格式（留空则通过 input() 询问，可选值见下方 SUPPORTED_EXTENSIONS）
SUFFIX: str = ""             # 导出后缀（设为空字符串则直接覆盖原文件名）

# 支持的格式列表
# key: 文件扩展名, value: (格式名称, 格式描述)
SUPPORTED_EXTENSIONS: Dict[str, Tuple[str, str]] = {
    '.obj':  ('OBJ',  'Wavefront OBJ (通用格式)'),
    '.stl':  ('STL',  'STereoLithography (3D打印)'),
    '.fbx':  ('FBX',  'Filmbox (通用交换格式)'),
    '.glb':  ('GLB',  'GLTF Binary (Web/游戏)'),
    '.gltf': ('GLTF', 'GLTF Text (Web/游戏)'),
    '.ply':  ('PLY',  'Polygon File Format (点云/扫描)'),
    '.x3d':  ('X3D',  'X3D (Web3D/VR)'),
}


# ============================================================
# 环境检测与模式选择
# ============================================================

def detect_engine() -> Optional[str]:
    """
    检测可用的减面引擎。
    返回: 'blender' 或 'trimesh' 或 None
    """
    # 先尝试 Blender 的 bpy
    try:
        import bpy  # type: ignore
        if hasattr(bpy, 'context') and hasattr(bpy, 'data') and hasattr(bpy, 'ops'):
            return 'blender'
    except ImportError:
        pass

    # 再尝试 trimesh
    try:
        import trimesh  # type: ignore
        return 'trimesh'
    except ImportError:
        pass

    return None


def print_engine_info(engine: str) -> None:
    """打印引擎信息"""
    if engine == 'blender':
        import bpy  # type: ignore
        print(f"[信息] 减面引擎: Blender bpy (v{bpy.app.version_string})")
    elif engine == 'trimesh':
        import trimesh  # type: ignore
        print(f"[信息] 减面引擎: trimesh (v{trimesh.__version__})")


def print_no_engine_guide() -> None:
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

def get_import_export_funcs() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    根据 Blender 版本返回对应的导入/导出函数映射。
    Blender 4.x 开始将部分导入算子迁移到 bpy.ops.wm.* 命名空间。
    """
    import bpy  # type: ignore

    version = bpy.app.version
    major = version[0]

    # 默认映射（Blender 3.x 及以下）
    import_map: Dict[str, Any] = {
        'OBJ':  bpy.ops.import_scene.obj,
        'STL':  bpy.ops.import_mesh.stl,
        'FBX':  bpy.ops.import_scene.fbx,
        'GLB':  bpy.ops.import_scene.gltf,
        'GLTF': bpy.ops.import_scene.gltf,
        'PLY':  bpy.ops.import_mesh.ply,
        'X3D':  bpy.ops.import_scene.x3d,
    }
    export_map: Dict[str, Any] = {
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


def blender_reset_scene() -> None:
    """重置 Blender 场景：删除所有对象并清理 orphan 数据块。"""
    import bpy  # type: ignore

    # 安全处理：检查场景是否为空
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.data.orphans_purge()


def blender_import_model(filepath: str) -> List[Any]:
    """使用 Blender 导入模型，返回新增对象列表。"""
    import bpy  # type: ignore

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


def blender_apply_decimate(objects: List[Any], ratio: float) -> Optional[Any]:
    """使用 Blender Decimate (Collapse) 修改器减面。"""
    import bpy  # type: ignore

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


def blender_export_model(obj: Any, output_path: str, target_ext: str) -> None:
    """使用 Blender 导出模型。"""
    import bpy  # type: ignore

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

def trimesh_load_model(filepath: str) -> Optional[Any]:
    """使用 trimesh 加载模型。"""
    import trimesh  # type: ignore

    mesh = trimesh.load(filepath)
    # 如果场景包含多个 mesh，合并为一个
    if isinstance(mesh, trimesh.Scene):
        print(f"  [信息] 场景包含多个 mesh，正在合并...")
        meshes = [
            geometry for geometry in mesh.geometry.values()
            if isinstance(geometry, trimesh.Trimesh)
        ]
        if not meshes:
            print("  [错误] 场景中未找到任何 Trimesh 对象")
            return None
        mesh = trimesh.util.concatenate(meshes)
    return mesh


def trimesh_apply_decimate(mesh: Any, ratio: float) -> Optional[Any]:
    """
    使用 trimesh 的简化算法进行减面。
    优先使用 fast_simplification（性能更好），
    回退使用 trimesh 内置的 simplify_quadric_decimation。
    """
    import trimesh  # type: ignore

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
        from fast_simplification import simplify  # type: ignore
        import numpy as np  # type: ignore

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


def trimesh_export_model(mesh: Any, output_path: str, target_ext: str) -> None:
    """使用 trimesh 导出模型。"""
    import trimesh  # type: ignore

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    ext = target_ext.lower()
    if ext in ('.glb', '.gltf', '.x3d'):
        # 这些格式需要包装为 Scene 导出
        scene = trimesh.Scene([mesh])
        file_type = ext.lstrip('.')
        scene.export(output_path, file_type=file_type)
    else:
        mesh.export(output_path)

    print(f"  [完成] 已导出: {output_path}")


# ============================================================
# 统一的处理流水线
# ============================================================

def process_file_blender(filepath: str, output_dir: str, ratio: float, output_ext: str) -> bool:
    """Blender 模式：处理单个文件。"""
    import bpy  # type: ignore

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


def process_file_trimesh(filepath: str, output_dir: str, ratio: float, output_ext: str) -> bool:
    """trimesh 模式：处理单个文件。"""
    import trimesh  # type: ignore

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


def _collect_files(input_dir: str) -> List[Union[str, Tuple[str, str]]]:
    """
    收集输入目录中所有支持的模型文件。
    返回文件路径列表（当 output_ext 固定时）或 (路径, 扩展名) 元组列表（当保持原格式时）。
    """
    files: List[Union[str, Tuple[str, str]]] = []
    for filename in os.listdir(input_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filepath = os.path.join(input_dir, filename)
            if os.path.isfile(filepath):
                files.append(filepath)
    files.sort()
    return files


def _print_batch_header(input_dir: str, output_dir: str, ratio: float,
                        output_ext: Optional[str], total: int) -> None:
    """打印批量处理的头部信息。"""
    if output_ext:
        fmt_info = SUPPORTED_EXTENSIONS.get(output_ext, ('未知', ''))
        output_fmt_name = fmt_info[0]
        fmt_line = f"# 输出格式: {output_fmt_name} ({output_ext})"
    else:
        fmt_line = "# 输出格式: 保持原格式"

    print(f"\n{'#'*60}")
    print(f"# 批量减面处理开始")
    print(f"# 输入目录: {input_dir}")
    print(f"# 输出目录: {output_dir}")
    print(f"# 塌陷比率: {ratio:.4f}")
    print(fmt_line)
    print(f"# 文件数量: {total}")
    print(f"{'#'*60}\n")


def _print_batch_footer(success_count: int, fail_count: int, total: int) -> None:
    """打印批量处理的尾部统计信息。"""
    print(f"\n{'#'*60}")
    print(f"# 批量处理完成")
    print(f"# 成功: {success_count}")
    print(f"# 失败: {fail_count}")
    print(f"# 总计: {total}")
    print(f"{'#'*60}")


def _run_batch_loop(files: List[Any], output_dir: str, ratio: float,
                    engine: str, keep_original_ext: bool = False) -> None:
    """
    执行批量处理循环。
    
    Args:
        files: 文件列表。如果 keep_original_ext=True，每个元素为 (path, ext) 元组；否则为路径字符串。
        output_dir: 输出目录
        ratio: 塌陷比率
        engine: 引擎类型 ('blender' 或 'trimesh')
        keep_original_ext: 是否保持原格式
    """
    process_func = process_file_blender if engine == 'blender' else process_file_trimesh
    total = len(files)
    success_count = 0
    fail_count = 0

    for idx, item in enumerate(files, 1):
        if keep_original_ext:
            filepath, orig_ext = item
        else:
            filepath = item
            orig_ext = None

        filename = os.path.basename(filepath)
        # 进度条显示
        progress_bar = _format_progress_bar(idx, total, width=20)
        print(f"\n>>> 进度: [{idx}/{total}] {progress_bar}")

        ext_to_use = orig_ext if keep_original_ext else item if isinstance(item, str) else orig_ext
        success = process_func(filepath, output_dir, ratio, ext_to_use)
        if success:
            success_count += 1
        else:
            fail_count += 1

    _print_batch_footer(success_count, fail_count, total)


def _format_progress_bar(current: int, total: int, width: int = 20) -> str:
    """生成文本进度条。"""
    if total == 0:
        return '[' + ' ' * width + ']'
    filled = int(width * current / total)
    bar = '█' * filled + '░' * (width - filled)
    return f'[{bar}]'


def batch_process(input_dir: str, output_dir: str, ratio: float,
                  output_ext: Optional[str], engine: str) -> None:
    """
    批量处理文件夹中的所有支持文件。
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        ratio: 塌陷比率
        output_ext: 输出扩展名（None 表示保持原格式）
        engine: 'blender' 或 'trimesh'
    """
    # 收集所有支持的文件
    raw_files = _collect_files(input_dir)
    if not raw_files:
        print(f"\n[信息] 在目录中未找到支持的模型文件: {input_dir}")
        print(f"[信息] 支持的格式: {', '.join(SUPPORTED_EXTENSIONS.keys())}")
        return

    total = len(raw_files)

    if output_ext:
        # 固定输出格式
        _print_batch_header(input_dir, output_dir, ratio, output_ext, total)
        _run_batch_loop(raw_files, output_dir, ratio, engine)
    else:
        # 保持原格式：将文件路径与扩展名配对
        files_with_ext: List[Tuple[str, str]] = []
        for filepath in raw_files:
            ext = os.path.splitext(filepath)[1].lower()
            files_with_ext.append((filepath, ext))

        _print_batch_header(input_dir, output_dir, ratio, None, total)
        _run_batch_loop(files_with_ext, output_dir, ratio, engine, keep_original_ext=True)


# ============================================================
# 交互式输入
# ============================================================

def _prompt_input_dir() -> str:
    """交互式获取输入目录。"""
    global INPUT_DIR
    if INPUT_DIR:
        return INPUT_DIR

    path = input("\n请输入输入文件夹路径 (待处理的模型文件): ").strip()
    if not path:
        print("[错误] 输入路径不能为空")
        sys.exit(1)
    if not os.path.isdir(path):
        print(f"[错误] 输入目录不存在: {path}")
        sys.exit(1)
    INPUT_DIR = path
    return path


def _prompt_output_dir() -> str:
    """交互式获取输出目录。"""
    global OUTPUT_DIR
    if OUTPUT_DIR:
        return OUTPUT_DIR

    path = input("请输入输出文件夹路径 (处理后文件的保存位置): ").strip()
    if not path:
        print("[错误] 输出路径不能为空")
        sys.exit(1)
    OUTPUT_DIR = path
    return path


def _prompt_ratio() -> float:
    """交互式获取塌陷比率。"""
    global RATIO
    if 0.0 < RATIO <= 1.0:
        return RATIO

    while True:
        try:
            ratio_input = input("请输入塌陷比率 (0.0 ~ 1.0, 例如 0.5 表示减掉 50% 的面数): ").strip()
            value = float(ratio_input)
            if 0.0 < value <= 1.0:
                RATIO = value
                return value
            else:
                print("[错误] 比率必须在 0.0 到 1.0 之间")
        except ValueError:
            print("[错误] 请输入有效的数字")


def _prompt_output_format() -> Optional[str]:
    """交互式获取输出格式。返回 None 表示保持原格式。"""
    global OUTPUT_FORMAT
    if OUTPUT_FORMAT:
        return OUTPUT_FORMAT

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
                return None
            idx = int(fmt_choice)
            if 1 <= idx <= len(format_list):
                selected_ext = format_list[idx - 1][0]
                OUTPUT_FORMAT = selected_ext
                return selected_ext
            else:
                print(f"[错误] 请输入 0 到 {len(format_list)} 之间的数字")
        except ValueError:
            print("[错误] 请输入有效的数字")


def _prompt_suffix() -> str:
    """交互式获取导出后缀。"""
    global SUFFIX
    suffix_input = input(f"\n请输入导出文件名后缀 (当前: '{SUFFIX}', 直接回车保持不变): ").strip()
    if suffix_input:
        SUFFIX = suffix_input
    return SUFFIX


def get_user_input() -> Tuple[str, str, float, Optional[str]]:
    """
    获取用户输入（路径和参数）。
    如果已在脚本顶部配置了值，则跳过对应的询问。
    
    Returns:
        (input_dir, output_dir, ratio, output_format)
        output_format 为 None 表示保持原格式
    """
    print("=" * 60)
    print("  自动化减面处理工具")
    print("=" * 60)

    input_dir = _prompt_input_dir()
    output_dir = _prompt_output_dir()
    ratio = _prompt_ratio()
    output_format = _prompt_output_format()
    _prompt_suffix()

    return input_dir, output_dir, ratio, output_format


# ============================================================
# 主入口
# ============================================================

def main() -> None:
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
    batch_process(input_dir, output_dir, ratio, output_format, engine)


if __name__ == "__main__":
    main()
