#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS功能组件公共基类
- 统一ROS环境管理与命令执行(env_cache缓存,避免重复source)
- 统一后台线程执行(async_helper线程安全回调)
- 统一定时器暂停/恢复接口
- 消除各widget重复代码
"""
import os
from PyQt6.QtWidgets import QWidget
from env_cache import run_cmd
from async_helper import run_async


class ROSWidget(QWidget):
    """所有ROS功能组件的基类"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup

    # ---------- ROS环境 ----------

    def set_ros_env(self, ros_setup, ws_setup):
        """设置ROS环境(自动缓存,命令执行更快)"""
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup

    def _run_cmd(self, cmd, timeout=8):
        """执行ROS命令(复用环境缓存,不用每次source)"""
        return run_cmd(cmd, self.ros_setup, self.ws_setup, timeout=timeout)

    def _run_bg(self, fn, on_done=None):
        """后台线程执行,完成后主线程回调(线程安全)"""
        run_async(fn, on_done)

    def _build_source_cmd(self):
        """兼容旧接口: 返回source命令串"""
        parts = []
        if self.ros_setup and os.path.exists(self.ros_setup):
            parts.append("source '%s'" % self.ros_setup)
        if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
            parts.append("source '%s'" % os.path.expanduser(self.ws_setup))
        return " && ".join(parts) if parts else ""

    # ---------- 定时器管理(子类覆写) ----------

    def pause_timers(self):
        """页面不可见时暂停定时器(子类覆写)"""
        pass

    def resume_timers(self):
        """页面可见时恢复定时器(子类覆写)"""
        pass
