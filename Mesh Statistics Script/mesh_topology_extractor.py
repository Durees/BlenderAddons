#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D 网格拓扑特征提取脚本
=======================
遍历指定目录下的 3D 模型文件，提取几何拓扑数据（顶点、边、面），
计算欧拉示性数与亏格，并将结果汇总导出为 CSV 文件。

依赖:
    pip install trimesh pandas tqdm
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import trimesh
from tqdm import tqdm


# 支持的模型文件扩展名（不区分大小写）
SUPPORTED_EXTENSIONS = {".obj", ".stl", ".ply", ".off", ".glb"}


def scan_model_files(root_dir: Path, recursive: bool = True) -> list[Path]:
    """
    扫描指定目录下所有受支持的 3D 模型文件。

    Args:
        root_dir: 根目录路径。
        recursive: 是否递归搜索子目录。

    Returns:
        匹配的模型文件路径列表。
    """
    if not root_dir.exists():
        print(f"[错误] 目录不存在: {root_dir}")
        return []

    if recursive:
        files = [p for p in root_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    else:
        files = [p for p in root_dir.glob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS]

    return sorted(files)


def process_mesh(file_path: Path) -> dict:
    """
    处理单个模型文件，提取拓扑特征。

    Args:
        file_path: 模型文件路径。

    Returns:
        包含提取结果的字典。
    """
    result = {
        "file_path": str(file_path),
        "file_name": file_path.name,
        "vertex_count": None,
        "edge_count": None,
        "face_count": None,
        "euler_characteristic": None,
        "genus": None,
        "is_watertight": None,
        "error": None,
    }

    try:
        # 加载模型
        mesh_or_scene = trimesh.load(str(file_path))

        # 如果是 Scene 对象，合并为单个网格
        if isinstance(mesh_or_scene, trimesh.Scene):
            mesh = mesh_or_scene.dump(concatenate=True)
        else:
            mesh = mesh_or_scene

        # 确保是 Trimesh 对象
        if not isinstance(mesh, trimesh.Trimesh):
            result["error"] = f"无法转换为 Trimesh 对象 (类型: {type(mesh).__name__})"
            return result

        # 基础计数
        v = len(mesh.vertices)
        f = len(mesh.faces)
        e = len(mesh.edges_unique)

        # 拓扑计算
        chi = v - e + f
        genus = 1 - (chi / 2)

        # 填充结果
        result["vertex_count"] = v
        result["edge_count"] = e
        result["face_count"] = f
        result["euler_characteristic"] = chi
        result["genus"] = genus
        result["is_watertight"] = bool(mesh.is_watertight)

    except Exception as exc:
        result["error"] = f"处理失败: {exc}"
        print(f"  [警告] 文件处理出错: {file_path} -> {exc}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="3D 网格拓扑特征提取工具 — 提取顶点、边、面、欧拉示性数、亏格等指标并导出 CSV。"
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="要扫描的文件夹路径（支持相对路径或绝对路径）",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="mesh_topology_results.csv",
        help="输出 CSV 文件路径（默认: mesh_topology_results.csv）",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="仅扫描当前文件夹，不递归子目录",
    )
    args = parser.parse_args()

    input_path = Path(args.input_dir).resolve()
    recursive = not args.no_recursive

    print(f"📁 扫描目录: {input_path}")
    print(f"🔁 递归搜索: {'是' if recursive else '否'}")
    print()

    # 扫描文件
    model_files = scan_model_files(input_path, recursive=recursive)

    if not model_files:
        print("未找到任何受支持的 3D 模型文件。")
        print(f"支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(0)

    print(f"找到 {len(model_files)} 个模型文件，开始处理...\n")

    # 处理所有模型文件（带进度条）
    records = []
    for file_path in tqdm(model_files, desc="处理进度", unit="file"):
        records.append(process_mesh(file_path))

    # 构建 DataFrame
    df = pd.DataFrame(records)

    # 统计成功/失败
    success_count = df["error"].isna().sum()
    error_count = df["error"].notna().sum()

    print(f"\n{'='*50}")
    print(f"✅ 成功处理: {success_count} 个文件")
    if error_count:
        print(f"❌ 处理失败: {error_count} 个文件")
    print(f"{'='*50}\n")

    # 导出 CSV（utf-8-sig 兼容 Excel）
    output_path = Path(args.output).resolve()
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"📄 结果已导出至: {output_path}")
    print(f"   共 {len(df)} 条记录，{len(df.columns)} 个字段。\n")

    # 打印简要摘要
    if success_count > 0:
        success_df = df[df["error"].isna()]
        print("📊 拓扑特征摘要（成功处理的文件）:")
        print(f"   顶点数范围: {success_df['vertex_count'].min()} ~ {success_df['vertex_count'].max()}")
        print(f"   面数范围:   {success_df['face_count'].min()} ~ {success_df['face_count'].max()}")
        print(f"   封闭流形:   {success_df['is_watertight'].sum()} / {len(success_df)} 个")
        print()


if __name__ == "__main__":
    main()
