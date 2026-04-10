第0步：创建环境
使用blender.yml文件创建conda环境
conda env create -n blender -f blender.yml

第1步：准备文件
将需要处理的OBJ文件放入 input/ 文件夹
（如果没有input文件夹，运行脚本会自动创建）


第2步：运行处理
python3 uv_processor.py

第3步：获取结果
处理后的文件在 Output/ 文件夹中


----------------------------------------
高级选项（可选）：

1. 仅检查环境：
   python3 uv_processor.py --check

2. 分批处理（适合100+文件）：
   python3 uv_processor.py --batch 20

3. 设置Blender路径（如果自动检测失败）：
   python3 uv_processor.py --set-blender "/path/to/blender"

4. 查看当前配置：
   python3 uv_processor.py --config

