# 安装指南

## 快速安装

### 方法一：通过 Blender 界面安装（推荐）

1. **下载插件包**
   - 从发布页面下载 `material_connection_validator.zip` 文件

2. **在 Blender 中安装**
   - 打开 Blender
   - 进入 `编辑(Edit) > 偏好设置(Preferences) > 插件(Add-ons)`
   - 点击右上角的 `安装(Install)` 按钮
   - 选择下载的 `material_connection_validator.zip` 文件
   - 点击 `安装插件(Install Add-on)`

3. **启用插件**
   - 在插件列表中搜索 "Material Connection Validator"
   - 勾选插件名称旁边的复选框以启用
   - 点击 `保存用户设置(Save User Settings)` 使插件在下次启动时自动加载

### 方法二：手动安装

1. **解压文件**
   ```bash
   unzip material_connection_validator.zip -d ~/blender_addons/
   ```

2. **复制到插件目录**
   - **Windows**:
     ```
     copy material_connection_validator "C:\Users\[用户名]\AppData\Roaming\Blender Foundation\Blender\[版本]\scripts\addons\"
     ```
   - **macOS**:
     ```
     cp -r material_connection_validator "/Users/[用户名]/Library/Application Support/Blender/[版本]/scripts/addons/"
     ```
   - **Linux**:
     ```
     cp -r material_connection_validator "/home/[用户名]/.config/blender/[版本]/scripts/addons/"
     ```

3. **在 Blender 中启用**
   - 打开 Blender
   - 进入 `编辑 > 偏好设置 > 插件`
   - 搜索 "Material Connection Validator"
   - 勾选启用

## 验证安装

安装完成后，可以通过以下方式验证插件是否正常工作：

1. **检查面板位置**
   - 在 3D 视图的右侧面板中，找到 "Material Tools" 标签页
   - 应该能看到 "材质连接验证器" 面板

2. **运行测试**
   - 创建一个测试材质
   - 点击 "验证所有材质" 按钮
   - 如果看到检测结果，说明插件安装成功

## 从源代码安装（开发者）

如果您想修改或扩展插件功能：

1. **克隆或下载源代码**
   ```bash
   git clone https://github.com/yourusername/material-connection-validator.git
   ```

2. **创建符号链接到插件目录**
   ```bash
   # macOS/Linux
   ln -s $(pwd)/material_connection_validator "/Users/[用户名]/Library/Application Support/Blender/[版本]/scripts/addons/material_connection_validator"
   
   # Windows (以管理员身份运行)
   mklink /D "C:\Users\[用户名]\AppData\Roaming\Blender Foundation\Blender\[版本]\scripts\addons\material_connection_validator" "[完整路径]\material_connection_validator"
   ```

3. **启用插件**
   - 在 Blender 中启用插件（同上）

4. **开发模式**
   - 修改代码后，在 Blender 中按 `F8` 重新加载脚本
   - 或使用插件面板中的重新加载功能

## 卸载插件

### 方法一：通过 Blender 界面卸载
1. 进入 `编辑 > 偏好设置 > 插件`
2. 找到 "Material Connection Validator"
3. 取消勾选以禁用
4. 点击右侧的 `移除(Remove)` 按钮

### 方法二：手动卸载
1. 删除插件目录：
   - **Windows**: `C:\Users\[用户名]\AppData\Roaming\Blender Foundation\Blender\[版本]\scripts\addons\material_connection_validator`
   - **macOS**: `/Users/[用户名]/Library/Application Support/Blender/[版本]/scripts/addons/material_connection_validator`
   - **Linux**: `/home/[用户名]/.config/blender/[版本]/scripts/addons/material_connection_validator`

## 故障排除

### 问题1：插件未出现在列表中
- **可能原因**：插件目录位置错误
- **解决方案**：检查 Blender 版本对应的正确插件目录

### 问题2：导入错误
- **可能原因**：Python 模块依赖问题
- **解决方案**：确保所有 `.py` 文件都在同一目录中

### 问题3：面板不显示
- **可能原因**：插件未正确启用
- **解决方案**：
  1. 检查插件是否已启用
  2. 检查 3D 视图的右侧面板，切换到 "Material Tools" 标签页
  3. 尝试切换工作空间到 "Shader Editor" 或 "Layout"

### 问题4：验证功能不工作
- **可能原因**：场景中没有使用节点的材质
- **解决方案**：创建一个使用节点编辑器的材质并测试

## 获取帮助

如果遇到问题，请：
1. 查看 [README.md](README.md) 中的常见问题解答
2. 检查控制台输出（Window > Toggle System Console）
3. 在 GitHub Issues 页面报告问题

## 系统要求

- **Blender**: 3.0 或更高版本
- **Python**: Blender 内置的 Python 3.x
- **操作系统**: Windows 10/11, macOS 10.15+, Linux

## 更新插件

要更新到新版本：

1. **备份当前设置**（如果有）
2. **卸载旧版本**
3. **安装新版本**
4. **恢复设置**（如果需要）

注意：插件设置通常存储在 Blender 的用户配置文件中，更新插件不会影响这些设置。