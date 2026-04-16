"""
Material Connection Validator - 单文件Blender插件
用于检测材质节点连接不正确的工具
"""

bl_info = {
    "name": "Material Connection Validator",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Material Tools",
    "description": "检测材质节点连接不正确的工具",
    "warning": "",
    "doc_url": "",
    "category": "Material",
}

import bpy
from bpy.types import Panel, Operator, UIList, PropertyGroup
from bpy.props import (StringProperty, BoolProperty, IntProperty, 
                      FloatProperty, EnumProperty, CollectionProperty)
from collections import defaultdict, deque

# ============================================================================
# 工具函数
# ============================================================================

def get_material_output_node(node_tree):
    """获取材质输出节点"""
    for node in node_tree.nodes:
        if node.type == 'OUTPUT_MATERIAL':
            return node
    return None

def get_node_dependencies(node_tree):
    """获取节点依赖关系图"""
    dependencies = defaultdict(list)
    reverse_dependencies = defaultdict(list)
    
    for link in node_tree.links:
        from_node = link.from_node
        to_node = link.to_node
        dependencies[from_node].append(to_node)
        reverse_dependencies[to_node].append(from_node)
    
    return dependencies, reverse_dependencies

def detect_cycles(node_tree):
    """检测节点循环依赖"""
    dependencies, _ = get_node_dependencies(node_tree)
    nodes = list(node_tree.nodes)
    
    # 使用Kahn算法检测循环
    in_degree = defaultdict(int)
    for node in nodes:
        in_degree[node] = 0
    
    for node in dependencies:
        for neighbor in dependencies[node]:
            in_degree[neighbor] += 1
    
    # 队列存储入度为0的节点
    queue = deque([node for node in nodes if in_degree[node] == 0])
    visited = 0
    
    while queue:
        node = queue.popleft()
        visited += 1
        
        for neighbor in dependencies[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # 如果访问的节点数不等于总节点数，说明有循环
    return visited != len(nodes)

def check_socket_compatibility(from_socket, to_socket):
    """检查两个插槽是否兼容"""
    # Blender插槽类型兼容性
    socket_types = {
        'RGBA': ['RGBA', 'VECTOR', 'VALUE'],
        'VECTOR': ['VECTOR', 'RGBA'],
        'VALUE': ['VALUE', 'RGBA', 'VECTOR'],
        'SHADER': ['SHADER'],
        'BOOLEAN': ['BOOLEAN', 'VALUE'],
        'INT': ['INT', 'VALUE'],
        'STRING': ['STRING'],
    }
    
    from_type = from_socket.type
    to_type = to_socket.type
    
    if from_type == to_type:
        return True
    
    compatible_types = socket_types.get(from_type, [])
    return to_type in compatible_types

def find_unconnected_inputs(node_tree, important_only=True):
    """查找未连接的输入插槽"""
    unconnected = []
    
    for node in node_tree.nodes:
        for input_socket in node.inputs:
            if not input_socket.enabled:
                continue
            
            connected = False
            for link in node_tree.links:
                if link.to_socket == input_socket:
                    connected = True
                    break
            
            if not connected:
                if important_only:
                    important_sockets = ['Base Color', 'Color', 'Emission', 'Surface', 
                                        'Normal', 'Roughness', 'Metallic', 'Alpha']
                    if input_socket.name in important_sockets:
                        unconnected.append((node, input_socket))
                else:
                    unconnected.append((node, input_socket))
    
    return unconnected

def find_unused_nodes(node_tree):
    """查找未被任何输出使用的节点"""
    output_node = get_material_output_node(node_tree)
    if not output_node:
        return []
    
    visited = set()
    
    def traverse_backwards(node):
        if node in visited:
            return
        visited.add(node)
        
        for input_socket in node.inputs:
            for link in node_tree.links:
                if link.to_socket == input_socket:
                    traverse_backwards(link.from_node)
    
    traverse_backwards(output_node)
    
    unused = []
    for node in node_tree.nodes:
        if node not in visited and node.type not in {'FRAME', 'REROUTE', 'GROUP_INPUT', 'GROUP_OUTPUT'}:
            unused.append(node)
    
    return unused

# ============================================================================
# 属性组
# ============================================================================

class MaterialValidationResult(PropertyGroup):
    """材质验证结果的数据结构"""
    material_name: StringProperty(name="材质名称")
    object_name: StringProperty(name="对象名称")
    issue_type: StringProperty(name="问题类型")
    issue_description: StringProperty(name="问题描述")
    severity: IntProperty(name="严重程度", min=1, max=3)  # 1=警告, 2=错误, 3=严重
    node_name: StringProperty(name="节点名称")
    socket_name: StringProperty(name="插槽名称")

# ============================================================================
# 操作符
# ============================================================================

class MATERIAL_OT_validate_connections(Operator):
    """验证材质节点连接"""
    bl_idname = "material.validate_connections"
    bl_label = "验证材质连接"
    bl_description = "检查当前场景中所有材质的节点连接问题"
    bl_options = {'REGISTER', 'UNDO'}
    
    check_missing_connections: BoolProperty(
        name="检查缺失连接",
        description="检查应该有连接但未连接的插槽",
        default=True
    )
    
    check_type_mismatch: BoolProperty(
        name="检查类型不匹配",
        description="检查连接的数据类型是否匹配",
        default=True
    )
    
    check_cycles: BoolProperty(
        name="检查循环连接",
        description="检查节点之间的循环依赖",
        default=True
    )
    
    check_unused_nodes: BoolProperty(
        name="检查未使用节点",
        description="检查未被任何输出使用的节点",
        default=True
    )
    
    def execute(self, context):
        # 清空之前的结果
        context.scene.material_validator_results.clear()
        
        # 收集所有材质
        materials = self.get_all_materials(context)
        
        # 验证每个材质
        for mat in materials:
            self.validate_material(context, mat)
        
        # 显示结果
        result_count = len(context.scene.material_validator_results)
        if result_count == 0:
            self.report({'INFO'}, f"验证完成：未发现连接问题")
        else:
            self.report({'WARNING'}, f"验证完成：发现 {result_count} 个问题")
        
        return {'FINISHED'}
    
    def get_all_materials(self, context):
        """获取场景中所有材质"""
        materials = []
        
        for obj in context.scene.objects:
            if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
                for slot in obj.material_slots:
                    if slot.material and slot.material not in materials:
                        materials.append(slot.material)
        
        for mat in bpy.data.materials:
            if mat not in materials:
                materials.append(mat)
        
        return materials
    
    def validate_material(self, context, material):
        """验证单个材质的节点连接"""
        if not material.use_nodes:
            self.add_result(
                context, material, None,
                "未使用节点", "材质未启用节点编辑器",
                1, None, None
            )
            return
        
        node_tree = material.node_tree
        if not node_tree:
            return
        
        nodes = node_tree.nodes
        links = node_tree.links
        
        # 检查缺失连接
        if self.check_missing_connections:
            self.check_missing_inputs(context, material, nodes, links)
        
        # 检查类型不匹配
        if self.check_type_mismatch:
            self.check_socket_type_mismatch(context, material, links)
        
        # 检查循环连接
        if self.check_cycles:
            self.check_cycle_connections(context, material, nodes, links)
        
        # 检查未使用节点
        if self.check_unused_nodes:
            self.check_unused_node(context, material, nodes, links)
    
    def check_missing_inputs(self, context, material, nodes, links):
        """检查重要节点的缺失输入连接"""
        important_nodes = ['BSDF', 'EMISSION', 'MIX_SHADER', 'ADD_SHADER', 'OUTPUT']
        
        for node in nodes:
            node_type = node.type if hasattr(node, 'type') else node.bl_idname
            
            if any(important in node_type for important in important_nodes):
                for input in node.inputs:
                    if not input.enabled:
                        continue
                    
                    has_link = False
                    for link in links:
                        if link.to_socket == input:
                            has_link = True
                            break
                    
                    if not has_link and input.name in ['Base Color', 'Color', 'Emission', 'Surface']:
                        self.add_result(
                            context, material, node,
                            "缺失连接", f"节点 '{node.name}' 的 '{input.name}' 输入未连接",
                            2, node.name, input.name
                        )
    
    def check_socket_type_mismatch(self, context, material, links):
        """检查连接的类型不匹配"""
        for link in links:
            from_socket = link.from_socket
            to_socket = link.to_socket
            
            if not check_socket_compatibility(from_socket, to_socket):
                self.add_result(
                    context, material, None,
                    "类型不匹配", 
                    f"连接类型不匹配: {from_socket.type} -> {to_socket.type} (从 '{from_socket.node.name}.{from_socket.name}' 到 '{to_socket.node.name}.{to_socket.name}')",
                    2, from_socket.node.name, from_socket.name
                )
    
    def check_cycle_connections(self, context, material, nodes, links):
        """检查循环连接"""
        if detect_cycles(material.node_tree):
            self.add_result(
                context, material, None,
                "循环连接", "检测到循环连接",
                3, None, None
            )
    
    def check_unused_node(self, context, material, nodes, links):
        """检查未使用的节点"""
        unused_nodes = find_unused_nodes(material.node_tree)
        for node in unused_nodes:
            self.add_result(
                context, material, node,
                "未使用节点", f"节点 '{node.name}' 未被任何输出使用",
                1, node.name, None
            )
    
    def add_result(self, context, material, node, issue_type, description, severity, node_name, socket_name):
        """添加验证结果"""
        result = context.scene.material_validator_results.add()
        result.material_name = material.name
        result.issue_type = issue_type
        result.issue_description = description
        result.severity = severity
        result.node_name = node_name if node_name else ""
        result.socket_name = socket_name if socket_name else ""

class MATERIAL_OT_select_problem_node(Operator):
    """选择有问题的节点"""
    bl_idname = "material.select_problem_node"
    bl_label = "选择节点"
    bl_description = "在节点编辑器中选中问题节点"
    bl_options = {'REGISTER', 'UNDO'}
    
    material_name: StringProperty()
    node_name: StringProperty()
    
    def execute(self, context):
        material = bpy.data.materials.get(self.material_name)
        if not material or not material.use_nodes:
            self.report({'WARNING'}, f"材质 '{self.material_name}' 未找到或未使用节点")
            return {'CANCELLED'}
        
        area = None
        for a in context.screen.areas:
            if a.type == 'NODE_EDITOR':
                area = a
                break
        
        if area:
            area.spaces.active.node_tree = material.node_tree
            
            node_tree = material.node_tree
            target_node = None
            for node in node_tree.nodes:
                if node.name == self.node_name:
                    target_node = node
                    break
            
            if target_node:
                for node in node_tree.nodes:
                    node.select = False
                
                target_node.select = True
                node_tree.nodes.active = target_node
                area.spaces.active.cursor_location = target_node.location
                
                self.report({'INFO'}, f"已选中节点 '{self.node_name}'")
            else:
                self.report({'WARNING'}, f"节点 '{self.node_name}' 未找到")
        else:
            self.report({'WARNING'}, "请先打开节点编辑器")
        
        return {'FINISHED'}

class MATERIAL_OT_fix_missing_connections(Operator):
    """自动修复缺失连接"""
    bl_idname = "material.fix_missing_connections"
    bl_label = "修复缺失连接"
    bl_description = "尝试自动修复缺失的连接"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        fixed_count = 0
        
        for result in context.scene.material_validator_results:
            if result.issue_type == "缺失连接":
                material = bpy.data.materials.get(result.material_name)
                if material and material.use_nodes and material.node_tree:
                    node_tree = material.node_tree
                    
                    # 查找节点和插槽
                    target_node = None
                    target_socket = None
                    
                    for node in node_tree.nodes:
                        if node.name == result.node_name:
                            target_node = node
                            for socket in node.inputs:
                                if socket.name == result.socket_name:
                                    target_socket = socket
                                    break
                            break
                    
                    if target_node and target_socket:
                        # 根据插槽类型添加默认节点
                        socket_type = target_socket.type.lower()
                        
                        if socket_type in ['rgba', 'vector']:
                            color_node = node_tree.nodes.new('ShaderNodeRGB')
                            color_node.location = (target_node.location.x - 300, target_node.location.y)
                            color_node.outputs[0].default_value = (0.8, 0.8, 0.8, 1.0)
                            node_tree.links.new(color_node.outputs[0], target_socket)
                            fixed_count += 1
                        
                        elif socket_type == 'value':
                            value_node = node_tree.nodes.new('ShaderNodeValue')
                            value_node.location = (target_node.location.x - 300, target_node.location.y)
                            value_node.outputs[0].default_value = 0.5
                            node_tree.links.new(value_node.outputs[0], target_socket)
                            fixed_count += 1
        
        if fixed_count > 0:
            self.report({'INFO'}, f"已修复 {fixed_count} 个缺失连接")
        else:
            self.report({'INFO'}, "没有需要修复的缺失连接")
        
        return {'FINISHED'}

# ============================================================================
# 用户界面
# ============================================================================

class MATERIAL_UL_validation_results(UIList):
    """验证结果列表"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.severity == 1:
                icon = 'INFO'
            elif item.severity == 2:
                icon = 'ERROR'
            else:
                icon = 'CANCEL'
            
            row = layout.row(align=True)
            row.label(text=item.material_name, icon='MATERIAL')
            
            split = layout.split(factor=0.3)
            split.label(text=item.issue_type)
            split.label(text=item.issue_description)
            
            if item.node_name:
                op = row.operator("material.select_problem_node", 
                                 text="", icon='NODE')
                op.material_name = item.material_name
                op.node_name = item.node_name
        
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=icon)

class MATERIAL_PT_connection_validator(Panel):
    """材质连接验证器主面板"""
    bl_label = "材质连接验证器"
    bl_idname = "MATERIAL_PT_connection_validator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Material Tools"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 验证设置
        box = layout.box()
        box.label(text="验证设置", icon='SETTINGS')
        
        col = box.column(align=True)
        col.prop(scene, "material_validator_show_details")
        
        # 验证按钮
        row = layout.row()
        op = row.operator("material.validate_connections", 
                         text="验证所有材质", 
                         icon='CHECKMARK')
        op.check_missing_connections = True
        op.check_type_mismatch = True
        op.check_cycles = True
        op.check_unused_nodes = True
        
        # 结果显示
        if scene.material_validator_results:
            layout.separator()
            
            total = len(scene.material_validator_results)
            errors = sum(1 for r in scene.material_validator_results if r.severity >= 2)
            warnings = total - errors
            
            stats_box = layout.box()
            stats_row = stats_box.row()
            stats_row.label(text=f"发现 {total} 个问题", icon='ERROR')
            stats_row.label(text=f"错误: {errors}", icon='CANCEL')
            stats_row.label(text=f"警告: {warnings}", icon='INFO')
            
            # 结果列表
            layout.template_list(
                "MATERIAL_UL_validation_results",
                "",
                scene,
                "material_validator_results",
                scene,
                "material