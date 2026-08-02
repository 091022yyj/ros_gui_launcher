#!/bin/bash
# ============================================
# ROS GUI启动器 一键发布脚本
# 用法: ./publish.sh [版本号]
# 流程: 打包exe -> 构建deb -> 上传GitHub -> 安装本机
# ============================================

set -e
cd "$(dirname "$0")"

TOKEN="${GITHUB_TOKEN:-}"
VERSION="${1:-3.4.1}"

echo "========================================"
echo " ROS GUI启动器 一键发布 v$VERSION"
echo "========================================"

# 1. 更新版本号
echo "[1/5] 更新版本号..."
sed -i "s/VERSION = \".*\"/VERSION = \"$VERSION\"/" launcher_gui.py
sed -i "s/\"current_version\": \".*\"/\"current_version\": \"$VERSION\"/" update_config.json
echo "  VERSION = $VERSION"

# 2. 打包可执行文件
echo "[2/5] 打包可执行文件..."
python3 build.py

# 3. 构建deb
echo "[3/5] 构建deb包..."
rm -f dist/*.deb
./build_deb.sh "$VERSION"

# 4. 上传GitHub Release
echo "[4/5] 上传GitHub Release..."
python3 - << PYEOF
from publish_update import load_config, create_github_release
config = load_config()
release = create_github_release(config, "$TOKEN", config["current_version"])
if release:
    print(f"发布成功: {release['html_url']}")
PYEOF

# 5. 安装到本机
echo "[5/5] 安装到本机..."
if [ -f dist/ros-gui-launcher_${VERSION}_amd64.deb ]; then
    sudo -S dpkg -i dist/ros-gui-launcher_${VERSION}_amd64.deb <<< "1" | tail -2
    # 更新桌面快捷方式
    cp icon.png "/home/ub/桌面/ros-gui-launcher.png" 2>/dev/null || true
else
    echo "警告: 找不到deb包,跳过安装"
fi

# 提交推送代码
echo ""
echo "提交代码到GitHub..."
git add -A
git commit -m "v$VERSION: 发布新版本" || echo "无变更提交"
git push origin main || echo "推送失败(网络问题,稍后重试)"

echo ""
echo "========================================"
echo " 发布完成!"
echo " Release: https://github.com/091022yyj/ros_gui_launcher/releases/tag/v$VERSION"
echo "========================================"
