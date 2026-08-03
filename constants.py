#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享常量与工具
- BASE_DIR/CONFIG_FILE/LOG_DIR/VERSION等全局常量
- DEFAULT_CONFIG默认配置
- normalize_task配置兼容工具
- 供launcher_gui.py与各mixin模块共用(避免循环导入)
"""
import os
import sys

# PyInstaller 打包后 __file__ 指向临时解压目录,
# 配置和日志要放在可执行文件旁边,否则每次运行都会丢失
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
VERSION = "4.0.0"

DEFAULT_CONFIG = {
    "ros_setup": "/opt/ros/noetic/setup.bash",
    "ws_setup": "",  # 例如 ~/catkin_ws/devel/setup.bash
    "start_delay": 3,  # 顺序启动时每个任务之间的延时(秒)
    "launch_files": [],
    "py_files": [],
    "history": [],  # 历史记录
    "current_scene": None,  # 当前场景
    "scenes": {},  # 场景配置
    "translation_enabled": True,  # 启用翻译
    "hotkeys": {
        "start_all": "F5",
        "stop_all": "F6",
        "start_selected": "F7",
        "stop_selected": "F8",
    },
}

MAX_RESTARTS = 3  # 崩溃自动重启的最大次数

# 表格列
COL_STATUS, COL_PATH, COL_ARGS, COL_RESTART, COL_AUTOSTART, COL_OPS = range(6)


def normalize_task(entry):
    """配置项兼容:字符串(旧格式)或字典"""
    if isinstance(entry, str):
        return {"path": entry, "args": "", "auto_restart": False, "auto_start": False}
    task = {"path": "", "args": "", "auto_restart": False, "auto_start": False}
    task.update(entry)
    return task
