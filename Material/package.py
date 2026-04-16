#!/usr/bin/env python3
"""
Material Connection Validator 打包脚本
用于创建可直接安装的Blender插件包
"""

import os
import zipfile
import shutil
from pathlib import Path

def create_zip_package():
    """创建ZIP格式的插件包（正确目录结构）"""
    
    # 插件名称和版本
    plugin_name = "material_connection_validator"
    version = "1.0.0"
    
    # 输出文件名
    output_zip = f"{plugin_name}_v{version}.zip"
    
    # 需要包含的文件（在插件目录内）
    required_files = [
        "__init__.py",
        "operators.py",
        "panels.py",
        "utils.py"
    ]
    
    # 文档文件（可选包含）
    doc_files = [
        "README.md",
        "INSTALL.md",
        "LICENSE"
    ]
    
    # 可选文件（如果存在）
    optional_files = [
        "test_material_validator.py",
        "examples/",
        "icons/"
    ]
    
    print(f"正在创建插件包: {output_zip}")
    print(f"版本: {version}")
    print("-" * 50)
    
    # 检查必需文件
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("错误：以下必需文件缺失:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    # 创建ZIP文件
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加必需文件到插件目录
            for file in required_files:
                if os.path.exists(file):
                    arcname = f"{plugin_name}/{file}"
                    print(f"添加: {file} -> {arcname}")
                    zipf.write(file, arcname=arcname)
            
            # 添加文档文件到插件目录
            for file in doc_files:
                if os.path.exists(file):
                    arcname = f"{plugin_name}/{file}"
                    print(f"添加: {file} -> {arcname}")
                    zipf.write(file, arcname=arcname)
            
            # 添加可选文件
            for file in optional_files:
                if os.path.exists(file):
                    if os.path.isdir(file):
                        # 添加整个目录到插件目录
                        for root, dirs, files in os.walk(file):
                            for f in files:
                                filepath = os.path.join(root, f)
                                # 保持目录结构
                                rel_path = os.path.relpath(filepath, start='.')
                                arcname = f"{plugin_name}/{rel_path}"
                                print(f"添加: {rel_path} -> {arcname}")
                                zipf.write(filepath, arcname=arcname)
                    else:
                        arcname = f"{plugin_name}/{file}"
                        print(f"添加: {file} -> {arcname}")
                        zipf.write(file, arcname=arcname)
            
            # 添加插件信息文件到根目录
            plugin_info = f"""Plugin: Material Connection Validator
Version: {version}
Author: Your Name
Blender: 3.0+
Description: 检测材质节点连接不正确的工具
Installation: In Blender, go to Edit > Preferences > Add-ons, click Install and select this ZIP file.
"""
            zipf.writestr("README.txt", plugin_info)
        
        print("-" * 50)
        print(f"成功创建插件包: {output_zip}")
        
        # 验证ZIP文件结构
        print("\nZIP文件结构:")
        with zipfile.ZipFile(output_zip, 'r') as zipf:
            for name in zipf.namelist():
                print(f"  {name}")
        
        file_size = os.path.getsize(output_zip) / 1024
        print(f"\n文件大小: {file_size:.1f} KB")
        
        # 显示安装说明
        print("\n安装说明:")
        print("1. 在Blender中打开: 编辑 > 偏好设置 > 插件")
        print("2. 点击'安装'按钮，选择此ZIP文件")
        print("3. 搜索'Material Connection Validator'并启用")
        print("4. 在3D视图侧边栏的'Material Tools'中找到插件面板")
        
        return True
        
    except Exception as e:
        print(f"创建ZIP文件时出错: {e}")
        return False

def create_directory_package():
    """创建目录格式的插件包（用于开发）"""
    
    plugin_name = "material_connection_validator"
    target_dir = f"{plugin_name}_package"
    
    print(f"正在创建目录包: {target_dir}/")
    
    # 如果目录已存在，先删除
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    
    # 创建目录
    os.makedirs(target_dir, exist_ok=True)
    
    # 复制文件
    files_to_copy = [
        "__init__.py",
        "operators.py", 
        "panels.py",
        "utils.py",
        "README.md",
        "INSTALL.md",
        "test_material_validator.py"
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            print(f"复制: {file}")
            shutil.copy2(file, target_dir)
    
    # 创建LICENSE文件（如果不存在）
    license_file = os.path.join(target_dir, "LICENSE")
    if not os.path.exists("LICENSE"):
        with open(license_file, 'w') as f:
            f.write("""MIT License

Copyright (c) 2024 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""")
        print("创建: LICENSE (MIT许可证)")
    
    print(f"\n目录包创建完成: {target_dir}/")
    print(f"可以复制到Blender插件目录: scripts/addons/{plugin_name}/")
    
    return True

def verify_package():
    """验证插件包内容"""
    
    print("验证插件包内容...")
    
    # 检查必需文件
    required_files = ["__init__.py", "operators.py", "panels.py", "utils.py"]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"✗ 缺失: {file}")
            return False
        else:
            print(f"✓ 存在: {file}")
    
    # 检查__init__.py中的bl_info
    try:
        with open("__init__.py", 'r') as f:
            content = f.read()
            if 'bl_info' in content:
                print("✓ __init__.py 包含 bl_info")
            else:
                print("✗ __init__.py 缺少 bl_info")
                return False
    except:
        print("✗ 无法读取 __init__.py")
        return False
    
    # 检查Python语法
    import ast
    python_files = ["__init__.py", "operators.py", "panels.py", "utils.py"]
    
    for file in python_files:
        try:
            with open(file, 'r') as f:
                ast.parse(f.read())
            print(f"✓ {file} 语法正确")
        except SyntaxError as e:
            print(f"✗ {file} 语法错误: {e}")
            return False
    
    print("\n所有检查通过！")
    return True

def main():
    """主函数"""
    
    print("Material Connection Validator 打包工具")
    print("=" * 50)
    
    # 验证当前目录
    if not os.path.exists("__init__.py"):
        print("错误：请在插件目录中运行此脚本")
        return
    
    # 验证插件
    if not verify_package():
        print("\n验证失败，请修复问题后再试")
        return
    
    # 显示菜单
    print("\n请选择打包方式:")
    print("1. 创建ZIP安装包（用于分发）")
    print("2. 创建目录包（用于开发）")
    print("3. 仅验证")
    print("4. 退出")
    
    choice = input("\n请输入选择 (1-4): ").strip()
    
    if choice == "1":
        create_zip_package()
    elif choice == "2":
        create_directory_package()
    elif choice == "3":
        print("验证完成")
    elif choice == "4":
        print("退出")
    else:
        print("无效选择")

if __name__ == "__main__":
    main()