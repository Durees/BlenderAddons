#!/usr/bin/env python3

import os
import sys
import json
import time
import argparse
import subprocess
import traceback
from datetime import datetime
from pathlib import Path

# ============================================================================
# 配置部分
# ============================================================================

class Config:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "input_folder": "Input",
        "output_folder": "Output",
        # UV投影参数（与官方API完全一致）
        "uv_angle_limit": 66.0,         # Angle Limit：66°（将转换为弧度）
        "uv_island_margin": 0.0,        # Island Margin
        "uv_area_weight": 0.0,          # Area Weight（官方API参数名）
        "uv_correct_aspect": True,      # Correct Aspect
        "uv_scale_to_bounds": False,    # Scale to Bounds（官方默认值为False）
        # 系统参数
        "blender_path": None,           # 自动检测
        "batch_size": 20,               # 分批处理大小
    }
    
    @staticmethod
    def find_blender():
        """自动查找Blender安装路径"""
        common_paths = [
            # # macOS
            # "/Applications/Blender.app/Contents/MacOS/Blender",
            # "/Applications/Blender 5.01.app/Contents/MacOS/Blender",
            # "/Applications/Blender 5.0.app/Contents/MacOS/Blender",
            # "/Applications/Blender 4.5.app/Contents/MacOS/Blender",
            # Linux
            # "/usr/bin/blender",
            # "/usr/local/bin/blender",
            # "/home/chih/Downloads/Blender/blender-5.0.1-linux-x64/blender"
            # # Windows (在类Unix系统上不会找到，但保留)
            # "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
            # "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # 尝试在PATH中查找
        try:
            result = subprocess.run(["which", "blender"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    @classmethod
    def load_or_create(cls):
        """加载或创建配置"""
        config_file = "uv_processor_config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                print(f"✓ 加载配置文件: {config_file}")
            except:
                print(f"⚠ 配置文件损坏，使用默认配置")
                config = cls.DEFAULT_CONFIG.copy()
        else:
            config = cls.DEFAULT_CONFIG.copy()
            print("使用默认配置")
        
        # 自动检测Blender路径
        if not config.get("blender_path"):
            blender_path = cls.find_blender()
            if blender_path:
                config["blender_path"] = blender_path
                print(f"✓ 自动检测到Blender: {blender_path}")
            else:
                print("⚠ 未找到Blender，请手动配置blender_path")
        
        # 确保文件夹存在
        os.makedirs(config["input_folder"], exist_ok=True)
        os.makedirs(config["output_folder"], exist_ok=True)
        
        return config
    
    @classmethod
    def save(cls, config):
        """保存配置"""
        config_file = "uv_processor_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ 配置已保存: {config_file}")

# ============================================================================
# 环境检查部分
# ============================================================================

def check_environment(config):
    """检查运行环境"""
    print("\n" + "=" * 60)
    print("环境检查")
    print("=" * 60)
    
    issues = []
    
    # 检查Blender
    blender_path = config.get("blender_path")
    if not blender_path:
        issues.append("Blender未配置")
        print("✗ Blender: 未配置")
    elif not os.path.exists(blender_path):
        issues.append(f"Blender路径不存在: {blender_path}")
        print(f"✗ Blender: 路径不存在 - {blender_path}")
    else:
        print(f"✓ Blender: {blender_path}")
        # 检查版本
        try:
            result = subprocess.run([blender_path, "--version"], 
                                  capture_output=True, text=True, timeout=3)
            for line in result.stdout.split('\n'):
                if "Blender" in line:
                    print(f"  版本: {line.strip()}")
                    break
        except:
            print("  无法获取版本信息")
    
    # 检查输入文件夹
    input_folder = config["input_folder"]
    if not os.path.exists(input_folder):
        issues.append(f"输入文件夹不存在: {input_folder}")
        print(f"✗ 输入文件夹: 不存在 - {input_folder}")
    else:
        obj_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.obj')]
        print(f"✓ 输入文件夹: {input_folder} ({len(obj_files)} 个OBJ文件)")
    
    # 检查输出文件夹
    output_folder = config["output_folder"]
    if not os.path.exists(output_folder):
        print(f"⚠ 输出文件夹: 不存在，将自动创建 - {output_folder}")
        os.makedirs(output_folder, exist_ok=True)
    else:
        print(f"✓ 输出文件夹: {output_folder}")
    
    # 总结
    print("\n检查结果:")
    if issues:
        print("✗ 发现问题:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ 所有检查通过")
        return True

# ============================================================================
# 核心处理部分
# ============================================================================

def create_blender_script(config, files_to_process=None):
    """创建Blender处理脚本 - 从模板文件读取并替换参数"""
    # 读取模板文件
    template_file = "blender_script_template.py"
    if not os.path.exists(template_file):
        print(f"✗ 模板文件不存在: {template_file}")
        return None
    
    with open(template_file, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 替换参数
    replacements = {
        '{input_folder}': os.path.abspath(config["input_folder"]),
        '{output_folder}': os.path.abspath(config["output_folder"]),
        # UV投影参数（与官方API完全一致）
        '{uv_angle_limit}': str(config["uv_angle_limit"]),          # Angle Limit
        '{uv_island_margin}': str(config["uv_island_margin"]),      # Island Margin
        '{uv_area_weight}': str(config.get("uv_area_weight", 0.0)), # Area Weight（兼容旧配置）
        '{uv_correct_aspect}': str(config["uv_correct_aspect"]),    # Correct Aspect
        '{uv_scale_to_bounds}': str(config["uv_scale_to_bounds"])   # Scale to Bounds
    }
    
    script_content = template_content
    for placeholder, value in replacements.items():
        script_content = script_content.replace(placeholder, value)
    
    # 保存为临时脚本
    script_file = "temp_blender_script.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    return script_file

def run_processing(config):
    """运行处理"""
    print("\n" + "=" * 60)
    print("开始处理OBJ文件")
    print("=" * 60)
    
    # 创建Blender脚本
    script_file = create_blender_script(config)
    print(f"✓ 创建处理脚本: {script_file}")
    
    # 运行Blender
    blender_path = config["blender_path"]
    if not blender_path or not os.path.exists(blender_path):
        print(f"✗ Blender路径无效: {blender_path}")
        return False
    
    cmd = [blender_path, "--background", "--python", script_file]
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1小时超时
        
        print("\n" + "=" * 60)
        print("处理输出")
        print("=" * 60)
        print(result.stdout)
        
        if result.stderr:
            print("\n警告/错误信息:")
            print(result.stderr)
        
        # 清理临时脚本
        if os.path.exists(script_file):
            os.remove(script_file)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("✗ 处理超时（1小时）")
        return False
    except Exception as e:
        print(f"✗ 运行失败: {e}")
        return False

# ============================================================================
# 批量处理部分
# ============================================================================

def batch_process(config, batch_size=None):
    """分批处理"""
    if batch_size is None:
        batch_size = config.get("batch_size", 20)
    
    input_folder = config["input_folder"]
    obj_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.obj')]
    
    if not obj_files:
        print("没有找到OBJ文件")
        return False
    
    total_files = len(obj_files)
    num_batches = (total_files + batch_size - 1) // batch_size
    
    print(f"\n分批处理: {total_files} 个文件，分为 {num_batches} 批，每批最多 {batch_size} 个")
    
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_files)
        batch_files = obj_files[start_idx:end_idx]
        
        print(f"\n处理批次 {i+1}/{num_batches} ({len(batch_files)} 个文件)...")
        
        # 创建临时输入文件夹
        temp_input = f"temp_input_batch_{i+1}"
        os.makedirs(temp_input, exist_ok=True)
        
        # 复制文件
        for file in batch_files:
            src = os.path.join(input_folder, file)
            dst = os.path.join(temp_input, file)
            import shutil
            shutil.copy2(src, dst)
        
        # 更新配置
        batch_config = config.copy()
        batch_config["input_folder"] = temp_input
        
        # 运行处理
        if not run_processing(batch_config):
            print(f"批次 {i+1} 处理失败")
        
        # 清理临时文件夹
        import shutil
        shutil.rmtree(temp_input, ignore_errors=True)
    
    return True

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="URDF2Mesh UV处理器 - 一体化工具")
    parser.add_argument("--check", action="store_true", help="仅检查环境，不处理")
    parser.add_argument("--config", action="store_true", help="显示当前配置")
    parser.add_argument("--set-blender", help="设置Blender路径")
    parser.add_argument("--set-input", help="设置输入文件夹路径")
    parser.add_argument("--set-output", help="设置输出文件夹路径")
    parser.add_argument("--batch", type=int, help="分批处理，指定每批文件数量")
    
    args = parser.parse_args()
    
    # 移除logo显示
    
    # 加载配置
    config = Config.load_or_create()
    
    # 处理配置参数
    if args.set_blender:
        config["blender_path"] = args.set_blender
        Config.save(config)
        print(f"✓ Blender路径已设置为: {args.set_blender}")
        return
    
    if args.set_input:
        config["input_folder"] = args.set_input
        Config.save(config)
        print(f"✓ 输入文件夹已设置为: {args.set_input}")
        return
    
    if args.set_output:
        config["output_folder"] = args.set_output
        Config.save(config)
        print(f"✓ 输出文件夹已设置为: {args.set_output}")
        return
    
    # 显示配置
    if args.config:
        print("\n当前配置:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return
    
    # 检查环境
    if not check_environment(config):
        print("\n环境检查失败，请解决问题后重试")
        sys.exit(1)
    
    if args.check:
        print("\n环境检查完成，未执行处理")
        return
    
    # 运行处理
    if args.batch:
        success = batch_process(config, args.batch)
    else:
        success = run_processing(config)
    
    if success:
        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("处理失败")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()