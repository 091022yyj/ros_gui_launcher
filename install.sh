#!/bin/bash
# ROS GUI启动器 安装脚本
# 用法: sudo ./install.sh

set -e

APP_NAME="ros_gui_launcher"
SRC_DIR="$(dirname "$(readlink -f "$0")")"
INSTALL_DIR="/opt/$APP_NAME"

echo "========================================"
echo " ROS GUI 一键启动器 安装程序"
echo "========================================"

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then
    echo "错误: 请使用 sudo 运行此脚本"
    echo "用法: sudo ./install.sh"
    exit 1
fi

# 检查可执行文件是否存在
if [ ! -f "$SRC_DIR/dist/ros_gui_launcher" ]; then
    echo "错误: 找不到 dist/ros_gui_launcher"
    echo "请先运行: python3 build.py"
    exit 1
fi

echo ""
echo "[1/4] 复制程序文件到 $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp "$SRC_DIR/dist/ros_gui_launcher" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/ros_gui_launcher"

# 复制配置文件
for f in update_config.json style.qss; do
    if [ -f "$SRC_DIR/dist/$f" ]; then
        cp "$SRC_DIR/dist/$f" "$INSTALL_DIR/"
    fi
done

# 复制图标
if [ -f "$SRC_DIR/icon.png" ]; then
    cp "$SRC_DIR/icon.png" "$INSTALL_DIR/"
else
    echo "警告: 未找到 icon.png"
fi

echo "[2/4] 创建桌面快捷方式 ..."

# 生成桌面文件
DESKTOP_FILE="/usr/share/applications/ros-gui-launcher.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=ROS GUI启动器
Name[en]=ROS GUI Launcher
Comment=ROS 一键启动器
Exec=$INSTALL_DIR/ros_gui_launcher
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Development;Science;Robotics;
StartupNotify=true
StartupWMClass=ros_gui_launcher
EOF

chmod +x "$DESKTOP_FILE"

echo "[3/4] 创建卸载脚本 ..."
cat > "$INSTALL_DIR/uninstall.sh" << EOF
#!/bin/bash
echo "正在卸载 ROS GUI启动器..."
rm -rf $INSTALL_DIR
rm -f /usr/share/applications/ros-gui-launcher.desktop
echo "卸载完成"
EOF
chmod +x "$INSTALL_DIR/uninstall.sh"

echo "[4/4] 更新桌面数据库 ..."
update-desktop-database /usr/share/applications/ 2>/dev/null || true

echo ""
echo "========================================"
echo " 安装完成!"
echo ""
echo " 启动方式:"
echo "   - 应用菜单搜索 'ROS GUI启动器'"
echo "   - 或运行: $INSTALL_DIR/ros_gui_launcher"
echo ""
echo " 卸载方式: sudo $INSTALL_DIR/uninstall.sh"
echo "========================================"
