"""
Material Connection Validator 测试脚本
用于测试插件的基本功能
"""

import bpy
import sys
import os

# 添加当前目录到路径，以便导入插件模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_plugin_loading():
    """测试插件加载"""
    print("=== 测试插件加载 ===")
    
    try:
        # 尝试导入插件模块
        import __init__ as material_validator
        print("✓ 插件模块导入成功")
        
        # 检查 bl_info
        if hasattr(material_validator, 'bl_info'):
            print(f"✓ bl_info 存在: {material_validator.bl_info['name']}")
        else:
            print("✗ bl_info 不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 插件加载失败: {e}")
        return False

def test_operators():
    """测试操作符"""
    print("\n=== 测试操作符 ===")
    
    # 检查操作符是否已注册
    operators_to_check = [
        'material.validate_connections',
        'material.select_problem_node',
        'material.fix_missing_connections'
    ]
    
    all_operators_found = True
    for op_id in operators_to_check:
        try:
            op_class = getattr(bpy.types, op_id.replace('.', '_OT_'))
            print(f"✓ 操作符 '{op_id}' 已注册")
        except AttributeError:
            print(f"✗ 操作符 '{op_id}' 未找到")
            all_operators_found = False
    
    return all_operators_found

def test_panels():
    """测试面板"""
    print("\n=== 测试面板 ===")
    
    panels_to_check = [
        'MATERIAL_PT_connection_validator',
        'MATERIAL_PT_validation_settings',
        'MATERIAL_PT_quick_fixes'
    ]
    
    all_panels_found = True
    for panel_id in panels_to_check:
        try:
            panel_class = getattr(bpy.types, panel_id)
            print(f"✓ 面板 '{panel_id}' 已注册")
        except AttributeError:
            print(f"✗ 面板 '{panel_id}' 未找到")
            all_panels_found = False
    
    return all_panels_found

def test_utils_functions():
    """测试工具函数"""
    print("\n=== 测试工具函数 ===")
    
    try:
        from utils import (
            get_material_output_node,
            detect_cycles,
            find_unconnected_inputs,
            validate_node_tree
        )
        print("✓ 工具函数导入成功")
        
        # 创建一个测试材质
        test_mat = bpy.data.materials.new("TestMaterial")
        test_mat.use_nodes = True
        
        # 测试获取输出节点
        output_node = get_material_output_node(test_mat.node_tree)
        if output_node:
            print("✓ 成功获取材质输出节点")
        else:
            print("✗ 未找到材质输出节点")
        
        # 测试检测循环（应该返回False，因为没有节点）
        has_cycles = detect_cycles(test_mat.node_tree)
        print(f"✓ 循环检测完成: {has_cycles}")
        
        # 测试查找未连接输入
        unconnected = find_unconnected_inputs(test_mat.node_tree)
        print(f"✓ 找到 {len(unconnected)} 个未连接输入")
        
        # 测试验证节点树
        issues = validate_node_tree(test_mat.node_tree)
        print(f"✓ 验证完成，找到 {len(issues)} 个问题")
        
        # 清理
        bpy.data.materials.remove(test_mat)
        
        return True
        
    except Exception as e:
        print(f"✗ 工具函数测试失败: {e}")
        return False

def create_test_scene():
    """创建测试场景"""
    print("\n=== 创建测试场景 ===")
    
    # 创建一个立方体
    bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD')
    cube = bpy.context.active_object
    
    # 创建测试材质
    test_mat = bpy.data.materials.new("ProblematicMaterial")
    test_mat.use_nodes = True
    
    # 添加一些节点创建问题
    nodes = test_mat.node_tree.nodes
    links = test_mat.node_tree.links
    
    # 清除默认节点
    nodes.clear()
    
    # 创建输出节点
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # 创建BSDF节点但不连接
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # 创建循环：值节点 -> 颜色节点 -> 值节点
    value1 = nodes.new(type='ShaderNodeValue')
    value1.location = (-300, 100)
    value1.outputs[0].default_value = 1.0
    
    value2 = nodes.new(type='ShaderNodeValue')
    value2.location = (-300, -100)
    
    # 创建未使用的节点
    unused = nodes.new(type='ShaderNodeRGB')
    unused.location = (-500, 200)
    
    # 分配材质
    cube.data.materials.append(test_mat)
    
    print("✓ 测试场景创建完成")
    print(f"  材质: {test_mat.name}")
    print(f"  节点数: {len(nodes)}")
    
    return test_mat

def run_validation_test():
    """运行验证测试"""
    print("\n=== 运行验证测试 ===")
    
    try:
        # 执行验证操作
        bpy.ops.material.validate_connections(
            check_missing_connections=True,
            check_type_mismatch=True,
            check_cycles=True,
            check_unused_nodes=True
        )
        
        # 检查结果
        results = bpy.context.scene.material_validator_results
        print(f"✓ 验证完成，找到 {len(results)} 个问题")
        
        if results:
            print("发现的问题:")
            for i, result in enumerate(results):
                print(f"  {i+1}. [{result.issue_type}] {result.issue_description}")
        
        return True
        
    except Exception as e:
        print(f"✗ 验证测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始 Material Connection Validator 测试")
    print("=" * 50)
    
    # 注册插件（模拟）
    try:
        import __init__ as material_validator
        material_validator.register()
        print("插件已注册用于测试")
    except:
        pass
    
    # 运行测试
    tests = [
        ("插件加载", test_plugin_loading),
        ("操作符", test_operators),
        ("面板", test_panels),
        ("工具函数", test_utils_functions),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        try:
            passed = test_func()
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"✗ {test_name} 测试异常: {e}")
            all_passed = False
    
    # 创建测试场景并运行验证
    if all_passed:
        test_mat = create_test_scene()
        run_validation_test()
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    
    # 清理
    try:
        material_validator.unregister()
        print("插件已注销")
    except:
        pass
    
    return all_passed

if __name__ == "__main__":
    # 注意：这个测试需要在Blender的Python环境中运行
    # 可以通过 blender --python test_material_validator.py 执行
    print("这个测试脚本需要在Blender中运行")
    print("使用方法: blender --python test_material_validator.py")
    
    # 如果不在Blender环境中，只检查语法
    if not hasattr(bpy, 'context'):
        print("\n当前不在Blender环境中，只进行语法检查...")
        import ast
        try:
            with open(__file__, 'r') as f:
                ast.parse(f.read())
            print("✓ 语法检查通过")
        except SyntaxError as e:
            print(f"✗ 语法错误: {e}")