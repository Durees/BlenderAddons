"""
工具函数 - 材质连接检测的辅助函数
"""

import bpy
from collections import defaultdict, deque

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
    if visited != len(nodes):
        return True
    return False

def find_cycle_nodes(node_tree):
    """找到构成循环的节点"""
    dependencies, _ = get_node_dependencies(node_tree)
    nodes = list(node_tree.nodes)
    
    # 使用DFS找循环
    visited = set()
    on_stack = set()
    cycle = []
    
    def dfs(node, path):
        visited.add(node)
        on_stack.add(node)
        path.append(node)
        
        for neighbor in dependencies.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, path):
                    return True
            elif neighbor in on_stack:
                # 找到循环
                cycle_start = path.index(neighbor)
                global cycle
                cycle = path[cycle_start:]
                return True
        
        on_stack.remove(node)
        path.pop()
        return False
    
    for node in nodes:
        if node not in visited:
            if dfs(node, []):
                return cycle
    
    return []

def check_socket_compatibility(from_socket, to_socket):
    """检查两个插槽是否兼容"""
    # Blender插槽类型
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
    
    # 检查类型转换兼容性
    compatible_types = socket_types.get(from_type, [])
    return to_type in compatible_types

def find_unconnected_inputs(node_tree, important_only=True):
    """查找未连接的输入插槽"""
    unconnected = []
    
    for node in node_tree.nodes:
        for input_socket in node.inputs:
            # 跳过不可用的插槽
            if not input_socket.enabled:
                continue
            
            # 检查是否有连接
            connected = False
            for link in node_tree.links:
                if link.to_socket == input_socket:
                    connected = True
                    break
            
            if not connected:
                # 如果只检查重要的，过滤一些插槽
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
    
    # 从输出节点开始反向遍历
    visited = set()
    
    def traverse_backwards(node):
        if node in visited:
            return
        visited.add(node)
        
        # 遍历所有输入连接
        for input_socket in node.inputs:
            for link in node_tree.links:
                if link.to_socket == input_socket:
                    traverse_backwards(link.from_node)
    
    traverse_backwards(output_node)
    
    # 找出未访问的节点
    unused = []
    for node in node_tree.nodes:
        if node not in visited and node.type not in {'FRAME', 'REROUTE', 'GROUP_INPUT', 'GROUP_OUTPUT'}:
            unused.append(node)
    
    return unused

def validate_node_tree(node_tree):
    """全面验证节点树"""
    issues = []
    
    # 1. 检查循环
    if detect_cycles(node_tree):
        cycle_nodes = find_cycle_nodes(node_tree)
        if cycle_nodes:
            node_names = [node.name for node in cycle_nodes]
            issues.append({
                'type': 'CYCLE',
                'severity': 3,
                'description': f"检测到循环连接: {', '.join(node_names)}",
                'nodes': cycle_nodes
            })
    
    # 2. 检查未连接的重要输入
    unconnected = find_unconnected_inputs(node_tree, important_only=True)
    for node, socket in unconnected:
        issues.append({
            'type': 'MISSING_CONNECTION',
            'severity': 2,
            'description': f"节点 '{node.name}' 的 '{socket.name}' 输入未连接",
            'node': node,
            'socket': socket
        })
    
    # 3. 检查类型不匹配
    for link in node_tree.links:
        if not check_socket_compatibility(link.from_socket, link.to_socket):
            issues.append({
                'type': 'TYPE_MISMATCH',
                'severity': 2,
                'description': f"类型不匹配: {link.from_socket.type} -> {link.to_socket.type}",
                'link': link,
                'from_node': link.from_node,
                'to_node': link.to_node
            })
    
    # 4. 检查未使用的节点
    unused_nodes = find_unused_nodes(node_tree)
    for node in unused_nodes:
        issues.append({
            'type': 'UNUSED_NODE',
            'severity': 1,
            'description': f"节点 '{node.name}' 未被使用",
            'node': node
        })
    
    # 5. 检查无效的节点组
    for node in node_tree.nodes:
        if node.type == 'GROUP':
            if not node.node_tree:
                issues.append({
                    'type': 'INVALID_GROUP',
                    'severity': 2,
                    'description': f"节点组 '{node.name}' 没有关联的节点树",
                    'node': node
                })
    
    return issues

def get_material_info(material):
    """获取材质信息"""
    info = {
        'name': material.name,
        'use_nodes': material.use_nodes,
        'engine': material.use_nodes and material.node_tree and material.node_tree.type or 'NONE',
        'node_count': 0,
        'link_count': 0,
        'issues': []
    }
    
    if material.use_nodes and material.node_tree:
        info['node_count'] = len(material.node_tree.nodes)
        info['link_count'] = len(material.node_tree.links)
        info['issues'] = validate_node_tree(material.node_tree)
    
    return info

def format_issue_for_display(issue):
    """格式化问题用于显示"""
    severity_icons = {
        1: 'INFO',
        2: 'ERROR',
        3: 'CANCEL'
    }
    
    severity_colors = {
        1: (0.6, 0.6, 0.0, 1.0),  # 黄色
        2: (1.0, 0.3, 0.0, 1.0),  # 橙色
        3: (1.0, 0.0, 0.0, 1.0)   # 红色
    }
    
    return {
        'icon': severity_icons.get(issue['severity'], 'QUESTION'),
        'color': severity_colors.get(issue['severity'], (0.5, 0.5, 0.5, 1.0)),
        'text': issue['description']
    }

def auto_fix_missing_connection(node_tree, node, socket):
    """自动修复缺失的连接"""
    # 根据插槽类型添加默认节点
    socket_type = socket.type.lower()
    
    if socket_type in ['rgba', 'vector']:
        # 添加颜色节点
        color_node = node_tree.nodes.new('ShaderNodeRGB')
        color_node.location = (node.location.x - 300, node.location.y)
        color_node.outputs[0].default_value = (0.8, 0.8, 0.8, 1.0)
        
        # 连接
        node_tree.links.new(color_node.outputs[0], socket)
        return True
    
    elif socket_type == 'value':
        # 添加值节点
        value_node = node_tree.nodes.new('ShaderNodeValue')
        value_node.location = (node.location.x - 300, node.location.y)
        value_node.outputs[0].default_value = 0.5
        
        # 连接
        node_tree.links.new(value_node.outputs[0], socket)
        return True
    
    return False