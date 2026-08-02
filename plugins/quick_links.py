#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置插件: 常用命令快捷
- 提供 rosbag record -a、rosnode list、rqt_graph 等一键执行按钮
- 在新终端中 source 环境后执行命令
"""
import os
import shlex
import subprocess
import threading


def plugin_info():
    """插件元数据"""
    return {
        "name": "常用命令快捷",
        "description": "一键执行 rosbag record、rosnode list、rqt_graph 等常用命令",
        "version": "1.0.0",
        "author": "内置",
        "homepage": "",
    }


COMMANDS = [
    {
        "key": "rosbag_record_all",
        "name": "录制全部话题",
        "command": "rosbag record -a",
        "description": "录制所有话题到 rosbag 文件 (Ctrl+C 停止)",
    },
    {
        "key": "rosnode_list",
        "name": "列出节点",
        "command": "rosnode list",
        "description": "列出当前运行的 ROS 节点",
    },
    {
        "key": "rqt_graph",
        "name": "节点关系图",
        "command": "rqt_graph",
        "description": "打开 ROS 节点话题关系可视化图",
    },
    {
        "key": "rostopic_list",
        "name": "列出话题",
        "command": "rostopic list",
        "description": "列出当前全部 ROS 话题",
    },
    {
        "key": "rviz",
        "name": "启动 RViz",
        "command": "rviz",
        "description": "启动机器人可视化工具 RViz",
    },
    {
        "key": "rosbag_info",
        "name": "查看 bag 信息",
        "command": "rosbag info --pause",
        "description": "交互式查看 rosbag 文件信息",
    },
]


def get_commands():
    """获取快捷命令列表"""
    return COMMANDS


def _find_setup_scripts():
    """查找可用的 ROS 环境脚本"""
    setups = []
    for path in ["/opt/ros/noetic/setup.bash",
                 "/opt/ros/kinetic/setup.bash",
                 os.path.expanduser("~/catkin_ws/devel/setup.bash"),
                 os.path.expanduser("~/ros_ws/devel/setup.bash")]:
        if os.path.exists(path):
            setups.append(path)
    if os.environ.get("ROS_DISTRO"):
        setups.append(f"/opt/ros/{os.environ['ROS_DISTRO']}/setup.bash")
    return setups


def _find_terminal():
    """查找可用的终端模拟器"""
    for term in ["gnome-terminal", "x-terminal-emulator", "konsole", "xfce4-terminal", "xterm"]:
        try:
            subprocess.run(["which", term], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True)
            return term
        except (OSError, subprocess.CalledProcessError):
            continue
    return None


def _build_env_command(command):
    """构造带 ROS 环境加载的 bash 命令"""
    setups = _find_setup_scripts()
    env_parts = [f"source {shlex.quote(s)}" for s in setups if os.path.exists(s)]
    env_parts.append("exec " + command)
    return "bash -c " + shlex.quote("; ".join(env_parts))


def run_command(cmd_key):
    """在新终端中执行指定快捷命令, 返回执行结果"""
    cmd = None
    for c in COMMANDS:
        if c["key"] == cmd_key:
            cmd = c
            break
    if cmd is None:
        return {"success": False, "error": f"未知命令 '{cmd_key}'"}

    terminal = _find_terminal()
    if terminal is None:
        return {"success": False, "error": "未找到可用的终端模拟器"}

    try:
        full_cmd = _build_env_command(cmd["command"])
        if terminal == "gnome-terminal":
            args = [terminal, "--", full_cmd]
        elif terminal == "konsole":
            args = [terminal, "-e", full_cmd]
        else:
            args = [terminal, "-e", full_cmd]
        subprocess.Popen(args, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return {"success": True, "command": cmd["name"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_command_async(cmd_key):
    """异步执行命令 (不阻塞调用线程)"""
    result = {}

    def worker():
        result.update(run_command(cmd_key))

    threading.Thread(target=worker, daemon=True).start()
    return {"success": True, "started": True}


def plugin_unload():
    """卸载插件时的清理"""
    pass
