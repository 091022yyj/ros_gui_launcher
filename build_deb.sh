#!/bin/bash
# ROS GUI启动器 - deb打包脚本
# 用法: ./build_deb.sh [版本号]

set -e

cd "$(dirname "$0")"

VERSION="${1:-3.3.0}"
APP_NAME="ros-gui-launcher"
ARCH="amd64"
PKG_ROOT="/tmp/opencode/deb_root"
OUTPUT_DIR="dist"

echo "========================================"
echo " ROS GUI启动器 deb打包"
echo " 版本: $VERSION"
echo "========================================"

# 检查可执行文件
if [ ! -f "dist/ros_gui_launcher" ]; then
    echo "错误: 找不到 dist/ros_gui_launcher"
    echo "请先运行: python3 build.py"
    exit 1
fi

# 清理旧的构建目录
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/opt/$APP_NAME"
mkdir -p "$PKG_ROOT/usr/share/applications"
mkdir -p "$PKG_ROOT/usr/share/icons/hicolor/128x128/apps"

echo "[1/4] 复制程序文件..."
cp dist/ros_gui_launcher "$PKG_ROOT/opt/$APP_NAME/"
chmod +x "$PKG_ROOT/opt/$APP_NAME/ros_gui_launcher"

for f in update_config.json style.qss; do
    if [ -f "dist/$f" ]; then
        cp "dist/$f" "$PKG_ROOT/opt/$APP_NAME/"
    fi
done

# 复制plugins目录
if [ -d "dist/plugins" ]; then
    cp -r "dist/plugins" "$PKG_ROOT/opt/$APP_NAME/"
fi

if [ -f "icon.png" ]; then
    cp icon.png "$PKG_ROOT/usr/share/icons/hicolor/128x128/apps/ros-gui-launcher.png"
fi

echo "[2/4] 创建控制文件..."
SIZE=$(du -sk "$PKG_ROOT" | awk '{print $1}')
cat > "$PKG_ROOT/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: science
Priority: optional
Architecture: $ARCH
Depends: libc6 (>= 2.31), libqt5core5a (>= 5.12), libqt5gui5 (>= 5.12), libqt5widgets5 (>= 5.12), libx11-6
Installed-Size: $SIZE
Maintainer: ROS GUI Launcher <support@example.com>
Description: ROS 一键启动器
  ROS任务管理和远程控制GUI工具。
  - 一键启动/停止 launch 和 python 任务
  - 系统监控、日志管理
  - 远程SSH多机控制
  - 任务调度、场景管理
EOF

cat > "$PKG_ROOT/DEBIAN/postinst" << EOF
#!/bin/bash
chmod +x /opt/$APP_NAME/ros_gui_launcher
update-desktop-database /usr/share/applications/ 2>/dev/null || true
exit 0
EOF
chmod +x "$PKG_ROOT/DEBIAN/postinst"

cat > "$PKG_ROOT/DEBIAN/prerm" << EOF
#!/bin/bash
exit 0
EOF
chmod +x "$PKG_ROOT/DEBIAN/prerm"

echo "[3/4] 创建桌面快捷方式..."
cat > "$PKG_ROOT/usr/share/applications/ros-gui-launcher.desktop" << EOF
[Desktop Entry]
Type=Application
Name=ROS GUI启动器
Name[en]=ROS GUI Launcher
Comment=ROS 一键启动器
Exec=/opt/$APP_NAME/ros_gui_launcher
Icon=ros-gui-launcher
Terminal=false
Categories=Development;Science;Robotics;
StartupNotify=true
EOF

echo "[4/4] 打包..."
mkdir -p "$OUTPUT_DIR"
DEB_FILE="$OUTPUT_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$PKG_ROOT" "$DEB_FILE"

ls -lh "$DEB_FILE"
echo ""
echo "打包完成: $DEB_FILE"
echo "安装: sudo dpkg -i $DEB_FILE"
echo "卸载: sudo dpkg -r $APP_NAME"
