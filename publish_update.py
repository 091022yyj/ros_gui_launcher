#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布更新脚本
使用方法:
1. 修改 update_config.json 中的版本号
2. 运行 python3 publish_update.py
3. 按提示输入GitHub Token
"""
import os
import sys
import json
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "update_config.json"
DIST_DIR = BASE_DIR / "dist"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def build_application():
    """打包应用程序"""
    print("开始打包...")
    result = subprocess.run(
        [sys.executable, "build.py", "--clean"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("打包失败:")
        print(result.stderr)
        return False
    print("打包成功!")
    return True

def create_github_release(config, token, version):
    """创建GitHub Release并上传文件"""
    repo_owner = config["repo_owner"]
    repo_name = config["repo_name"]

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 创建Release
    release_data = {
        "tag_name": f"v{version}",
        "name": f"ROS GUI启动器 v{version}",
        "body": f"## 更新内容\n\n- 版本 {version} 更新\n\n## 下载\n\n- `ros_gui_launcher` 可执行文件(免安装,直接运行)\n- `ros-gui-launcher_*.deb` deb安装包(Ubuntu/Debian, sudo dpkg -i 安装)",
        "draft": False,
        "prerelease": False
    }

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
    response = requests.post(url, json=release_data, headers=headers)

    if response.status_code != 201:
        print(f"创建Release失败: {response.text}")
        return None

    release = response.json()
    release_id = release["id"]
    print(f"Release创建成功: {release['html_url']}")

    headers_upload = {
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream"
    }

    # 上传可执行文件
    executable_path = DIST_DIR / "ros_gui_launcher"
    if executable_path.exists():
        print("正在上传可执行文件...")
        upload_url = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/releases/{release_id}/assets?name=ros_gui_launcher"
        with open(executable_path, "rb") as f:
            response = requests.post(upload_url, data=f, headers=headers_upload)
        if response.status_code == 201:
            print("可执行文件上传成功!")
        else:
            print(f"可执行文件上传失败: {response.text}")

    # 上传deb安装包
    deb_files = list(DIST_DIR.glob("*.deb"))
    for deb_path in deb_files:
        print(f"正在上传deb安装包: {deb_path.name} ...")
        upload_url = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/releases/{release_id}/assets?name={deb_path.name}"
        with open(deb_path, "rb") as f:
            response = requests.post(upload_url, data=f, headers=headers_upload)
        if response.status_code == 201:
            print(f"deb包上传成功: {deb_path.name}")
        else:
            print(f"deb包上传失败: {deb_path.name} - {response.text}")

    return release

def main():
    config = load_config()
    version = config["current_version"]

    print(f"当前版本: {version}")
    new_version = input("请输入新版本号 (直接回车保持当前版本): ").strip()
    if new_version:
        config["current_version"] = new_version
        save_config(config)
        version = new_version

    print(f"即将发布版本: v{version}")

    # 打包
    if not build_application():
        return

    # 获取GitHub Token
    token = input("请输入GitHub Personal Access Token: ").strip()
    if not token:
        print("未输入Token，取消发布")
        return

    # 创建Release并上传
    release = create_github_release(config, token, version)
    if release:
        print(f"\n发布成功!")
        print(f"Release地址: {release['html_url']}")
        print(f"\n用户可以通过程序内的'检查更新'按钮获取更新")

if __name__ == "__main__":
    main()
