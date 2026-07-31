# ROS GUI启动器

一个用于管理ROS进程的图形界面启动器。

## 功能特性

- 一键启动/停止多个ROS进程
- 实时监控进程状态和资源使用
- 自动崩溃重启
- 远程更新支持
- 多平台打包

## 安装

### 从源码安装

```bash
git clone https://github.com/user/ros_gui_launcher.git
cd ros_gui_launcher
pip install -r requirements.txt
python launcher_gui.py
```

### 打包安装

```bash
python build.py
./dist/ros_gui_launcher
```

## 使用说明

1. 配置ROS环境路径
2. 添加launch文件或Python文件
3. 点击"启动"按钮

## 开发

### 运行测试

```bash
python -m pytest tests/
```

### 打包

```bash
python build.py --clean
```

## 许可证

MIT License