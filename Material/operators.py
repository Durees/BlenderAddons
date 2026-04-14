"""
操作符定义 - 包含材质验证的主要逻辑
"""

import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty

class MaterialValidationResult(PropertyGroup):
    """材质验证结果的数据结构"""
    material_name: StringProperty(name="材质名称")
    object_name: StringProperty(name="对象名称")
    issue_type: StringProperty(name="问题类型")
    issue_description: StringProperty(name="问题描述")
    severity: IntProperty(name="严重程度", min=1, max=3)  # 1=警告, 2=错误, 3=严重
    node_name: StringProperty(name="节点名称")
    socket_name: StringProperty(name="插槽名称")

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
        
        # 从对象获取材质
        for obj in context.scene.objects:
            if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
                for slot in obj.material_slots:
                    if slot.material and slot.material not in materials:
                        materials.append(slot.material)
        
        # 从材质库获取
        for mat in bpy.data.materials:
            if mat not in materials:
                materials.append(mat)
        
        return materials
    
    def validate_material(self, context, material):
        """验证单个材质的节点连接"""
        if not material.use_nodes:
            # 如果没有使用节点，添加警告
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
            
            # 检查重要节点
            if any(important in node_type for important in important_nodes):
                for input in node.inputs:
                    # 跳过不需要连接的插槽
                    if not input.enabled:
                        continue
                    
                    # 检查是否有连接
                    has_link = False
                    for link in links:
                        if link.to_socket == input:
                            has_link = True
                            break
                    
                    # 如果重要插槽没有连接，添加警告
                    if not has_link and input.name in ['Base Color', 'Color', 'Emission', 'Surface']:
                        self.add_result(
                            context, material, node,
                            "缺失连接", f"节点 '{node.name}' 的 '{input.name}' 输入未连接",
                            2, node.name, input.name
                        )
    
    def check_socket_type_mismatch(self, context, material, links):
        """检查连接的类型不匹配"""
        # 这里简化处理，实际需要更复杂的类型检查
        for link in links:
            from_socket = link.from_socket
            to_socket = link.to_socket
            
            # 检查颜色/向量/值类型
            from_type = self.get_socket_type(from_socket)
            to_type = self.get_socket_type(to_socket)
            
            if from_type != to_type and from_type != 'ANY' and to_type != 'ANY':
                self.add_result(
                    context, material, None,
                    "类型不匹配", 
                    f"连接类型不匹配: {from_type} -> {to_type} (从 '{from_socket.node.name}.{from_socket.name}' 到 '{to_socket.node.name}.{to_socket.name}')",
                    2, from_socket.node.name, from_socket.name
                )
    
    def get_socket_type(self, socket):
        """获取插槽类型"""
        if hasattr(socket, 'type'):
            return socket.type
        return 'UNKNOWN'
    
    def check_cycle_connections(self, context, material, nodes, links):
        """检查循环连接"""
        # 构建邻接表
        graph = {node: [] for node in nodes}
        for link in links:
            if link.from_node in graph:
                graph[link.from_node].append(link.to_node)
        
        # 使用DFS检测循环
        visited = set()
        recursion_stack = set()
        
        def dfs(node):
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    # 发现循环
                    self.add_result(
                        context, material, node,
                        "循环连接", f"检测到循环连接涉及节点 '{node.name}'",
                        3, node.name, None
                    )
                    return True
            
            recursion_stack.remove(node)
            return False
        
        for node in nodes:
            if node not in visited:
                if dfs(node):
                    # 已报告循环
                    pass
    
    def check_unused_node(self, context, material, nodes, links):
        """检查未使用的节点"""
        # 找到输出节点
        output_nodes = [node for node in nodes if node.type == 'OUTPUT_MATERIAL']
        if not output_nodes:
            return
        
        # 从输出节点开始反向遍历，标记所有可达节点
        reachable = set()
        
        def traverse_from_output(node):
            if node in reachable:
                return
            reachable.add(node)
            
            # 遍历所有输入连接
            for input in node.inputs:
                for link in links:
                    if link.to_socket == input:
                        traverse_from_output(link.from_node)
        
        for output_node in output_nodes:
            traverse_from_output(output_node)
        
        # 检查未到达的节点
        for node in nodes:
            if node not in reachable and node.type not in {'FRAME', 'REROUTE', 'GROUP_INPUT', 'GROUP_OUTPUT'}:
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
        # 查找材质
        material = bpy.data.materials.get(self.material_name)
        if not material or not material.use_nodes:
            self.report({'WARNING'}, f"材质 '{self.material_name}' 未找到或未使用节点")
            return {'CANCELLED'}
        
        # 切换到节点编辑器
        area = None
        for a in context.screen.areas:
            if a.type == 'NODE_EDITOR':
                area = a
                break
        
        if area:
            # 设置活动材质
            area.spaces.active.node_tree = material.node_tree
            
            # 查找并选中节点
            node_tree = material.node_tree
            target_node = None
            for node in node_tree.nodes:
                if node.name == self.node_name:
                    target_node = node
                    break
            
            if target_node:
                # 取消选择所有节点
                for node in node_tree.nodes:
                    node.select = False
                
                # 选中目标节点
                target_node.select = True
                node_tree.nodes.active = target_node
                
                # 视图居中
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
        # 这里可以实现自动修复逻辑
        # 例如：为缺失的颜色输入添加默认颜色节点
        
        self.report({'INFO'}, "修复功能尚未实现")
        return {'FINISHED'}

# 注册的类列表
classes = [
    MaterialValidationResult,
    MATERIAL_OT_validate_connections,
    MATERIAL_OT_select_problem_node,
    MATERIAL_OT_fix_missing_connections,
]