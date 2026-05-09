#!/usr/bin/env python3
"""
批量 Smart UV Project — 终端 CLI 版本
========================================
版本: 5.0
描述: 输入文件夹路径，对其中所有 .obj / .fbx 文件的网格物体
      执行 Smart UV Project，结果保存到输出子目录。

用法:
  python batch_smart_uv_project_cli.py
  python batch_smart_uv_project_cli.py /path/to/models
  python batch_smart_uv_project_cli.py /path/to/models --angle-limit 45 --island-margin 0.01
  python batch_smart_uv_project_cli.py /path/to/models --clear
  python batch_smart_uv_project_cli.py /path/to/models --action clear
  python batch_smart_uv_project_cli.py /path/to/models --recursive --dry-run
  python batch_smart_uv_project_cli.py /path/to/models --subdir uv_output --verbose

  # Blender 内置 Python:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python batch_smart_uv_project_cli.py -- /path/to/models

依赖: bpy (pip install bpy, 或在 Blender 内置 Python 中运行)

变更 (v5.0):
  - 修复: angle_limit 现在自动从角度转换为弧度（Blender API 要求）
  - 新增: --recursive 递归扫描子文件夹
  - 新增: --dry-run 预览模式
  - 新增: --verbose 详细日志
  - 新增: --subdir 自定义输出子目录名
  - 新增: --correct-aspect / --no-correct-aspect
  - 新增: --scale-to-bounds
  - 新增: --rotate-method
  - 新增: --margin-method
  - 改进: pathlib 文件收集，自动处理大小写
  - 改进: 批量处理后自动清理孤儿数据块
  - 改进: 总耗时与进度百分比
  - 精简: 移除冗余的 import_bpy / _bpy 全局变量模式
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path


# ── bpy 懒加载 ────────────────────────────────────────────────────────

def _import_bpy():
    """导入 bpy 模块，失败时打印帮助信息并退出。"""
    try:
        import bpy
        _ = bpy.app.version_string   # 验证完全初始化
        return bpy
    except ImportError:
        print("=" * 50)
        print("错误: 未安装 bpy 模块")
        print("=" * 50)
        print()
        print("当前 Python:", sys.executable)
        print()
        print("方案1: pip install bpy")
        print("方案2: 用 Blender 内置 Python 运行")
        print("  /Applications/Blender.app/Contents/MacOS/Blender \\")
        print("    --background --python batch_smart_uv_project_cli.py -- /path/to/models")
        print()
        sys.exit(1)
    except AttributeError as e:
        print(f"错误: bpy 模块未完全初始化: {e}")
        print("尝试: pip uninstall bpy -y && pip install bpy")
        sys.exit(1)


# ── 文件发现 ──────────────────────────────────────────────────────────

SUPPORTED_SUFFIXES = {".obj", ".fbx"}


def collect_model_files(input_dir: Path, *, recursive: bool = False) -> list[Path]:
    """收集输入目录下所有支持的模型文件（不区分大小写）。"""
    if recursive:
        candidates = input_dir.rglob("*")
    else:
        candidates = input_dir.glob("*")

    files = [
        p for p in candidates
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    files.sort()
    return files


# ── 场景清理 ──────────────────────────────────────────────────────────

def clear_scene_objects(bpy):
    """删除场景中的所有物体。"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def clear_orphan_data(bpy):
    """清理无用户的网格 / 材质 / 图像等数据块，防止内存堆积。"""
    for data_attr in ("meshes", "materials", "images", "textures"):
        collection = getattr(bpy.data, data_attr, None)
        if collection is None:
            continue
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


# ── 导入 / 导出 ───────────────────────────────────────────────────────

def import_file(bpy, filepath: Path):
    """导入模型文件，返回 (成功, 错误信息)。"""
    ext = filepath.suffix.lower()
    try:
        if ext == ".obj":
            bpy.ops.wm.obj_import(filepath=str(filepath))
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(filepath))
        else:
            bpy.ops.wm.obj_import(filepath=str(filepath))
        return True, None
    except Exception as e:
        return False, f"导入失败: {e}"


def export_file(bpy, mesh_objects: list, output_path: Path):
    """导出选中的网格物体。返回 (成功, 错误信息)。"""
    ext = output_path.suffix.lower()
    try:
        if ext == ".obj":
            bpy.ops.wm.obj_export(
                filepath=str(output_path),
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
        elif ext == ".fbx":
            bpy.ops.export_scene.fbx(
                filepath=str(output_path),
                use_selection=True,
                apply_scale_options='FBX_SCALE_UNITS',
                object_types={'MESH'},
            )
        else:
            return False, f"不支持的导出格式: {ext}"
        return True, None
    except Exception as e:
        return False, f"导出失败: {e}"


# ── UV 操作 ───────────────────────────────────────────────────────────

def _select_only(obj, bpy):
    """取消全部选择后只选中指定物体并设为活动物体。"""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _enter_edit_select_all(bpy):
    """进入编辑模式并全选。"""
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')


def _to_object_mode(bpy):
    """安全返回物体模式。"""
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError:
        pass


def apply_clear_uv(bpy, mesh_objects: list) -> tuple[int, int, list[str]]:
    """清除网格物体的 UV 贴图。返回 (成功数, 失败数, 错误列表)。"""
    success, failed = 0, 0
    errors: list[str] = []

    for obj in mesh_objects:
        try:
            if not obj.data.uv_layers:
                continue
            _select_only(obj, bpy)
            _enter_edit_select_all(bpy)
            bpy.ops.uv.reset()
            _to_object_mode(bpy)
            obj.select_set(False)
            success += 1
        except Exception as e:
            failed += 1
            errors.append(f"{obj.name}: {e}")
            _to_object_mode(bpy)

    return success, failed, errors


def apply_smart_uv_project(
    bpy,
    mesh_objects: list,
    *,
    angle_limit: float,
    island_margin: float,
    area_weight: float,
    correct_aspect: bool,
    scale_to_bounds: bool,
    margin_method: str,
    rotate_method: str,
    clear_first: bool,
    verbose: bool,
) -> tuple[int, int, list[str]]:
    """对网格物体执行 Smart UV Project。返回 (成功数, 失败数, 错误列表)。"""
    success, failed = 0, 0
    errors: list[str] = []

    for obj in mesh_objects:
        try:
            _select_only(obj, bpy)

            # 可选：先清除现有 UV
            if clear_first and obj.data.uv_layers:
                _enter_edit_select_all(bpy)
                bpy.ops.uv.reset()
                _to_object_mode(bpy)

            _enter_edit_select_all(bpy)
            bpy.ops.uv.smart_project(
                angle_limit=math.radians(angle_limit),
                margin_method=margin_method,
                rotate_method=rotate_method,
                island_margin=island_margin,
                area_weight=area_weight,
                correct_aspect=correct_aspect,
                scale_to_bounds=scale_to_bounds,
            )
            _to_object_mode(bpy)
            obj.select_set(False)
            success += 1

            if verbose:
                uv_count = len(obj.data.uv_layers)
                print(f"    ✓ {obj.name}  UV层:{uv_count}")

        except Exception as e:
            failed += 1
            errors.append(f"{obj.name}: {e}")
            _to_object_mode(bpy)

    return success, failed, errors


def select_objects(bpy, objects: list) -> None:
    """取消全选后选中给定物体列表。"""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)


# ── 单文件处理管线 ───────────────────────────────────────────────────

def process_single_file(
    bpy,
    input_file: Path,
    output_file: Path,
    *,
    angle_limit: float,
    island_margin: float,
    area_weight: float,
    correct_aspect: bool,
    scale_to_bounds: bool,
    margin_method: str,
    rotate_method: str,
    clear_first: bool,
    action: str,
    verbose: bool,
) -> dict:
    """处理单个文件：导入 → UV 操作 → 导出。返回结果字典。"""
    result = {
        "input": str(input_file),
        "output": str(output_file),
        "success": 0,
        "failed": 0,
        "errors": [],
    }

    # 1. 清空场景
    clear_scene_objects(bpy)

    # 2. 导入
    ok, err = import_file(bpy, input_file)
    if not ok:
        result["errors"].append(err)
        return result

    # 3. 获取网格物体
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objects:
        result["errors"].append("文件中没有网格物体")
        clear_orphan_data(bpy)
        return result

    # 4. UV 操作
    if action == "clear":
        s, f, errs = apply_clear_uv(bpy, mesh_objects)
    else:
        s, f, errs = apply_smart_uv_project(
            bpy, mesh_objects,
            angle_limit=angle_limit,
            island_margin=island_margin,
            area_weight=area_weight,
            correct_aspect=correct_aspect,
            scale_to_bounds=scale_to_bounds,
            margin_method=margin_method,
            rotate_method=rotate_method,
            clear_first=clear_first,
            verbose=verbose,
        )
    result["success"] = s
    result["failed"] = f
    result["errors"].extend(errs)

    # 5. 导出
    select_objects(bpy, mesh_objects)
    ok, err = export_file(bpy, mesh_objects, output_file)
    if not ok:
        result["errors"].append(err)

    # 6. 清理孤儿数据
    clear_orphan_data(bpy)

    return result


# ── 主流程 ────────────────────────────────────────────────────────────

def _parse_blender_args() -> list[str]:
    """处理 Blender -- 分隔符：提取 -- 之后的实际参数。"""
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        return sys.argv[idx + 1:]
    return sys.argv[1:]


def _build_parser() -> argparse.ArgumentParser:
    """构建参数解析器。"""
    parser = argparse.ArgumentParser(
        description="批量 Smart UV Project — 终端 CLI 版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                                           # 交互式询问路径
  %(prog)s /path/to/models                           # 直接指定路径
  %(prog)s /path/to/models --angle-limit 45 --island-margin 0.01
  %(prog)s /path/to/models --clear                   # 展开前清除现有 UV
  %(prog)s /path/to/models --action clear            # 仅清除 UV
  %(prog)s /path/to/models --recursive --dry-run     # 预览
  %(prog)s /path/to/models --subdir uv_output        # 自定义输出子目录

  # Blender 内置 Python:
  blender --background --python %(prog)s -- /path/to/models
        """,
    )

    parser.add_argument(
        "input_dir", nargs="?", default=None,
        help="输入文件夹路径（不提供则交互式询问）",
    )
    parser.add_argument(
        "--action", choices=["unwrap", "clear"], default="unwrap",
        help="操作: unwrap (展开UV) 或 clear (清除UV) (默认: unwrap)",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="展开前先清除现有 UV",
    )
    parser.add_argument(
        "--angle-limit", type=float, default=66.0,
        help="角度限制，单位 度 (默认: 66)",
    )
    parser.add_argument(
        "--island-margin", type=float, default=0.0,
        help="UV 岛屿间距 (默认: 0.0)",
    )
    parser.add_argument(
        "--area-weight", type=float, default=0.0,
        help="面积权重 (默认: 0.0)",
    )
    parser.add_argument(
        "--correct-aspect", action=argparse.BooleanOptionalAction, default=True,
        help="校正宽高比 (默认: on)",
    )
    parser.add_argument(
        "--scale-to-bounds", action="store_true", default=False,
        help="将 UV 缩放到 0-1 边界框内 (默认: off)",
    )
    parser.add_argument(
        "--rotate-method", default="AXIS_ALIGNED_Y",
        choices=["AXIS_ALIGNED_Y", "AXIS_ALIGNED_X", "CARDINAL", "GEOMETRY"],
        help="UV 岛旋转方法 (默认: AXIS_ALIGNED_Y)",
    )
    parser.add_argument(
        "--margin-method", default="SCALED",
        choices=["SCALED", "ADD", "FRACTION"],
        help="边距计算方法 (默认: SCALED)",
    )
    parser.add_argument(
        "--subdir", default="uv",
        help="输出子目录名 (默认: uv)",
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true",
        help="递归扫描子文件夹",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅列出待处理文件，不实际执行",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="显示每个物体的详细处理信息",
    )
    return parser


def _interactive_input_dir() -> str:
    """交互式询问输入文件夹路径。"""
    print("=" * 50)
    print("批量 Smart UV Project — 终端工具")
    print("=" * 50)
    path_str = input("\n请输入包含 .obj/.fbx 文件的文件夹路径: ").strip()
    path_str = path_str.strip("'\" ")
    path_str = os.path.expanduser(path_str)
    if not path_str:
        print("错误: 未输入文件夹路径")
        sys.exit(1)
    print()
    return path_str


def _print_result_line(i: int, total: int, filename: str,
                       success: int, failed: int, elapsed: float,
                       errors: list[str]) -> None:
    """打印单文件处理结果行。"""
    if failed == 0 and success > 0:
        status = f"✓ 完成 ({elapsed:.1f}s)"
    elif failed > 0:
        status = f"⚠ 部分完成  成功:{success}  失败:{failed} ({elapsed:.1f}s)"
    else:
        status = f"✗ 失败 ({elapsed:.1f}s)"

    pct = i * 100 // total if total else 100
    print(f"[{i}/{total} {pct:3d}%] {filename}")
    print(f"  {status}")
    for err in errors:
        print(f"    错误: {err}")


def _print_summary(file_count: int, total_success: int, total_failed: int,
                   output_dir: Path, elapsed: float) -> None:
    """打印汇总信息。"""
    print(f"\n{'=' * 50}")
    print("全部处理完成!")
    print(f"  处理文件数: {file_count}")
    print(f"  成功物体数: {total_success}")
    if total_failed > 0:
        print(f"  失败物体数: {total_failed}")
    print(f"  输出目录:   {output_dir}")
    print(f"  总耗时:     {elapsed:.1f}s")


def run(args: argparse.Namespace) -> int:
    """主执行逻辑。返回退出码。"""

    # 获取输入路径（无需 bpy）
    if args.input_dir:
        input_dir = Path(os.path.expanduser(args.input_dir))
    else:
        input_dir = Path(_interactive_input_dir())

    input_dir = input_dir.resolve()

    if not input_dir.is_dir():
        print(f"错误: 文件夹不存在: {input_dir}")
        return 1

    # 收集文件（无需 bpy）
    model_files = collect_model_files(input_dir, recursive=args.recursive)

    if not model_files:
        print(f"错误: 文件夹中没有找到 .obj 或 .fbx 文件: {input_dir}")
        return 1

    print(f"\n找到 {len(model_files)} 个模型文件")

    # 输出目录
    output_dir = input_dir / args.subdir

    # 干运行：仅列出（无需 bpy）
    if args.dry_run:
        print(f"\n[dry-run] 将处理以下文件 → {output_dir}/")
        for f in model_files:
            print(f"  {f.name}")
        return 0

    # 此后需要 bpy
    bpy = _import_bpy()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"输出文件夹: {output_dir}")

    # 初始化 Blender
    print("\n正在初始化 Blender Python 环境...")
    t_init = time.time()
    print(f"  Blender {bpy.app.version_string} 已就绪 ({time.time() - t_init:.1f}s)")

    # 批量处理
    total_success = 0
    total_failed = 0
    t_start = time.time()

    for i, file_path in enumerate(model_files, start=1):
        output_path = output_dir / file_path.name

        t_file = time.time()
        result = process_single_file(
            bpy, file_path, output_path,
            angle_limit=args.angle_limit,
            island_margin=args.island_margin,
            area_weight=args.area_weight,
            correct_aspect=args.correct_aspect,
            scale_to_bounds=args.scale_to_bounds,
            margin_method=args.margin_method,
            rotate_method=args.rotate_method,
            clear_first=args.clear,
            action=args.action,
            verbose=args.verbose,
        )
        elapsed_file = time.time() - t_file

        total_success += result["success"]
        total_failed += result["failed"]

        _print_result_line(
            i, len(model_files), file_path.name,
            result["success"], result["failed"],
            elapsed_file, result["errors"],
        )

    # 汇总
    _print_summary(
        len(model_files), total_success, total_failed,
        output_dir, time.time() - t_start,
    )
    return 0 if total_failed == 0 else 1


def main() -> None:
    """入口点。"""
    argv = _parse_blender_args()
    parser = _build_parser()
    args = parser.parse_args(argv)
    sys.exit(run(args))


if __name__ == "__main__":
    main()
