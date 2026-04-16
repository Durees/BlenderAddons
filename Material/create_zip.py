#!/usr/bin/env python3
"""
创建正确结构的Blender插件ZIP包
"""

import os
import zipfile

def create_correct_zip():
    """创建正确目录结构的ZIP包"""
    
    plugin_name = "material_connection_validator"
    version = "1.0.0"
    output_zip = f"{plugin_name}_v{version}_correct.zip"
    
    # 必需的核心文件
    core_files = [
        "__init__.py",
        "operators.py", 
        "panels.py",
        "utils.py"
    ]
    
    # 文档文件
    doc_files = [
        "README.md",
        "INSTALL.md",
        "LICENSE"
    ]
    
    # 可选文件
    optional_files = [
        "test_material_validator.py"
    ]
    
    print(f"创建Blender插件ZIP包: {output_zip}")
    print("=" * 60)
    
    # 检查文件是否存在
    missing = []
    for file in core_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print(f"错误：缺少必需文件: {missing}")
        return False
    
    # 创建ZIP文件
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 1. 添加核心文件到插件目录
            print("\n添加核心文件:")
            for file in core_files:
                arcname = f"{plugin_name}/{file}"
                print(f"  {file} -> {arcname}")
                zipf.write(file, arcname=arcname)
            
            # 2. 添加文档文件到插件目录
            print("\n添加文档文件:")
            for file in doc_files:
                if os.path.exists(file):
                    arcname = f"{plugin_name}/{file}"
                    print(f"  {file} -> {arcname}")
                    zipf.write(file, arcname=arcname)
            
            # 3. 添加可选文件
            print("\n添加可选文件:")
            for file in optional_files:
                if os.path.exists(file):
                    arcname = f"{plugin_name}/{file}"
                    print(f"  {file} -> {arcname}")
                    zipf.write(file, arcname=arcname)
            
            # 4. 添加安装说明
            install_note = """Material Connection Validator - Blender Add-on
Version: 1.0.0

INSTALLATION:
1. In Blender, go to Edit > Preferences > Add-ons
2. Click 'Install' button
3. Select this ZIP file
4. Search for 'Material Connection Validator' and enable it
5. Find the panel in 3D View sidebar under 'Material Tools' tab

FEATURES:
- Detects missing node connections
- Checks for type mismatches
- Finds cycle dependencies
- Identifies unused nodes
- Provides quick fixes

For more information, see README.md in the add-on directory.
"""
            zipf.writestr("INSTALLATION.txt", install_note)
        
        print("\n" + "=" * 60)
        print(f"成功创建: {output_zip}")
        
        # 显示ZIP内容
        print("\nZIP文件内容:")
        with zipfile.ZipFile(output_zip, 'r') as zipf:
            for name in sorted(zipf.namelist()):
                print(f"  {name}")
        
        file_size = os.path.getsize(output_zip)
        print(f"\n文件大小: {file_size / 1024:.1f} KB")
        
        # 验证结构
        print("\n验证结构:")
        with zipfile.ZipFile(output_zip, 'r') as zipf:
            has_init = False
            for name in zipf.namelist():
                if name.endswith("__init__.py"):
                    has_init = True
                    print(f"✓ 找到 __init__.py 在: {name}")
            
            if has_init:
                print("✓ 正确的Blender插件结构")
            else:
                print("✗ 错误的结构: __init__.py 不在ZIP中")
        
        return True
        
    except Exception as e:
        print(f"创建ZIP时出错: {e}")
        return False

if __name__ == "__main__":
    create_correct_zip()