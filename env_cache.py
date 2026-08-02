#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS环境缓存模块
- 一次性source获取环境变量,之后命令直接复用env,避免每次source(300ms->10ms)
- 提供快速命令执行函数
"""
import os
import subprocess

_cache = {}


def get_env(ros_setup="", ws_setup=""):
    """获取缓存的环境变量字典(首次source,之后复用)"""
    key = "%s|%s" % (ros_setup, ws_setup)
    if key in _cache:
        return _cache[key]

    parts = []
    if ros_setup and os.path.exists(ros_setup):
        parts.append("source '%s'" % ros_setup)
    if ws_setup and os.path.exists(os.path.expanduser(ws_setup)):
        parts.append("source '%s'" % os.path.expanduser(ws_setup))
    if not parts:
        _cache[key] = dict(os.environ)
        return _cache[key]

    cmd = " && ".join(parts) + " && env"
    try:
        result = subprocess.run(["bash", "-c", cmd], capture_output=True,
                                text=True, timeout=15)
        if result.returncode == 0:
            env = dict(os.environ)
            for line in result.stdout.split("\n"):
                if "=" in line:
                    k, _, v = line.partition("=")
                    env[k] = v
            _cache[key] = env
            return env
    except Exception:
        pass
    _cache[key] = dict(os.environ)
    return _cache[key]


def clear_cache():
    """清空缓存"""
    _cache.clear()


def run_cmd(cmd, ros_setup="", ws_setup="", timeout=8, use_cache=True):
    """快速执行ROS命令(复用环境缓存)"""
    env = get_env(ros_setup, ws_setup) if use_cache else dict(os.environ)
    try:
        result = subprocess.run(["bash", "-c", cmd], capture_output=True,
                                text=True, timeout=timeout, env=env)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", 1
    except Exception as e:
        return "", str(e), 1
