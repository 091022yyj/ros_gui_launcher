# ROS GUI 启动器 v3.6.7

一个功能强大的ROS一键启动工具，支持launch文件和Python脚本的管理与启动。

## 新增功能 (v3.0)

### 核心功能
- **日志分离系统** - 按任务分文件存储日志，支持日志过滤和搜索
- **ROS报错翻译** - 自动检测英文报错并翻译成中文
- **启动场景预设** - 保存/切换常用任务组合（建图、导航等）
- **内置终端** - 在GUI中直接运行ROS命令

### 易用性提升
- **文件拖拽支持** - 拖拽文件到窗口自动添加
- **历史记录** - 快速加载之前使用的文件
- **自动翻译** - 日志中的错误信息自动翻译成中文

## 安装

### 方式1：直接运行Python脚本

```bash
pip install PyQt5 psutil
python3 launcher_gui.py
```

### 方式2：打包成可执行文件

```bash
python3 build.py --clean
./dist/ros_gui_launcher
```

## 使用方法

### 基本使用
1. 设置ROS环境路径（ROS setup和工作空间setup）
2. 添加launch文件或Python文件到对应列表
3. 点击"一键启动所有任务"或单独启动

### 场景管理
1. 点击"场景管理"标签页
2. 点击"创建场景"保存当前配置
3. 双击场景可快速切换

### 内置终端
1. 点击"内置终端"标签页
2. 输入ROS命令（如 `rostopic list`）
3. 支持常用命令快捷按钮

### 日志查看
1. 点击"运行日志"标签页
2. 支持按任务过滤日志
3. 支持日志搜索

### 翻译工具
1. 点击"翻译工具"标签页
2. 输入英文错误信息
3. 获取中文翻译

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| F5 | 一键启动所有任务 |
| F6 | 停止所有任务 |
| F7 | 启动选中任务 |
| F8 | 停止选中任务 |
| ↑/↓ | 终端命令历史 |

## 文件结构

```
ros_gui_launcher/
├── launcher_gui.py      # 主程序
├── security.py          # 安全模块
├── config_manager.py    # 配置管理
├── monitor.py           # 系统监控
├── updater.py           # 远程更新
├── log_manager.py       # 日志管理
├── ros_translator.py    # ROS报错翻译
├── scene_manager.py     # 场景管理
├── terminal_widget.py   # 内置终端
├── build.py             # 打包脚本
└── update_config.json   # 更新配置
```

## 许可证

MIT License
