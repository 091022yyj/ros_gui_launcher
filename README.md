# ros_gui_launcher

ROS 一键启动图形界面（Python + PyQt5），把 launch 文件、Python 脚本、内置终端和日志管理全部收进一个窗口。新手不用再被满屏英文报错劝退（自动翻译成中文），launch 文件再多也不乱——比 rqt_launch 更贴近实战，比 Foxglove 更轻量。

![Version](https://img.shields.io/github/v/release/091022yyj/ros_gui_launcher)
![License](https://img.shields.io/github/license/091022yyj/ros_gui_launcher)
![Language](https://img.shields.io/badge/Language-Python-3776AB)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20ROS1%2FROS2-orange)

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🚀 一键启动 | 拖入 launch 文件或 Python 脚本，双击直接启动，不用背命令 |
| 🧠 报错中文翻译 | 自动截获 ROS 报错并翻译成中文，附常见解决建议，完全离线 |
| 📁 场景预设 | 常用启动组合存成预设，一键恢复整套环境 |
| 🖥️ 内置终端 | 集成终端面板，日志按节点分 Tab，互不干扰 |
| 📜 日志分离 | 每个节点独立日志区，ERROR/WARN 高亮显示 |
| 🖱️ 文件拖拽 | 直接拖文件进窗口，自动识别 launch / py / 目录类型 |

## 📸 截图

| 主界面 | 报错翻译 | 场景预设 |
|--------|----------|----------|
| ![主界面](docs/screenshot-main.png) | ![报错翻译](docs/screenshot-translate.png) | ![场景预设](docs/screenshot-presets.png) |

## 🚀 快速开始

```bash
# 依赖：ROS Noetic / Humble + Python 3
sudo apt install python3-pyqt5
git clone https://github.com/091022yyj/ros_gui_launcher.git
cd ros_gui_launcher
python3 main.py
```

## ❓ FAQ

**Q: 报错翻译怎么实现的？需要联网吗？**
A: 截获节点 stderr 后做本地规则匹配 + 词典翻译，完全离线；词典可自行编辑扩充。

**Q: 支持 ROS 2 吗？**
A: 支持，已验证 Noetic（ROS1）与 Humble（ROS2）。

**Q: 怎么添加自定义启动项？**
A: 直接把 launch 文件或脚本拖进窗口即可自动识别加入，右键可设置启动参数。

**Q: 翻译不准或想补充新报错怎么办？**
A: 编辑 `config/error_dict.json` 添加规则，重启程序即生效。

## 🏷️ 推荐 Topics

`ros` `ros2` `pyqt5` `gui` `robotics` `launch` `ros-tools` `chinese`
