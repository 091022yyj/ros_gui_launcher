#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置插件: ROS 时间
- 显示当前 ROS 时间与系统时间之差
- 检测时钟同步状态 (/use_sim_time 与 /clock 话题)
"""
import time
import threading


def plugin_info():
    """插件元数据"""
    return {
        "name": "ROS时间",
        "description": "显示当前 ROS 时间/系统时间差，检测时钟同步状态",
        "version": "1.0.0",
        "author": "内置",
        "homepage": "",
    }


def _try_rospy():
    """惰性导入 rospy, 避免未安装 ROS 时插件加载失败"""
    try:
        import rospy
        return rospy
    except ImportError:
        return None


def _system_time():
    """获取系统时间"""
    now = time.time()
    return {
        "epoch": now,
        "str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
    }


def _ros_time(rospy):
    """获取 ROS 时间"""
    if rospy.is_shutdown():
        return None
    try:
        now = rospy.Time.now()
        use_sim = rospy.get_param("/use_sim_time", False)
    except Exception:
        return None
    return {
        "epoch": now.to_sec(),
        "str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now.to_sec())),
        "use_sim_time": bool(use_sim),
    }


def _clock_topic_info(rospy):
    """检测 /clock 话题的发布者"""
    try:
        pubs = rospy.get_published_topics()
    except Exception:
        return None
    for topic, mtype in pubs:
        if topic == "/clock":
            return {"topic": topic, "type": mtype}
    return None


def get_time_info():
    """获取 ROS 时间与系统时间对比信息"""
    info = {"system": _system_time()}
    rospy = _try_rospy()
    if rospy is None:
        info["available"] = False
        info["error"] = "未检测到 ROS 环境 (rospy 不可用)"
        return info

    info["available"] = True
    info["ros"] = _ros_time(rospy)
    info["clock_topic"] = _clock_topic_info(rospy)

    if info["ros"] is None:
        info["error"] = "ROS 未启动或已关闭"
        return info

    diff = info["ros"]["epoch"] - info["system"]["epoch"]
    info["diff_sec"] = round(diff, 3)
    if info["ros"]["use_sim_time"]:
        if info["clock_topic"] is None:
            info["synced"] = False
            info["sync_status"] = "仿真时间模式下未检测到 /clock 话题, 时钟可能未同步"
        else:
            info["synced"] = True
            info["sync_status"] = "仿真时间模式, /clock 话题正常, 时间由仿真驱动"
    elif abs(diff) > 1.0:
        info["synced"] = False
        info["sync_status"] = f"时钟偏差 {info['diff_sec']} 秒, 存在漂移, 建议检查 NTP 同步"
    else:
        info["synced"] = True
        info["sync_status"] = "ROS 时间与系统时间一致"
    return info


def format_report():
    """生成可读的 ROS 时间报告文本"""
    info = get_time_info()
    lines = ["===== ROS 时间 ====="]
    sys_t = info["system"]
    lines.append(f"系统时间: {sys_t['str']}")
    if not info.get("available"):
        lines.append(f"状态:     {info.get('error', 'ROS 不可用')}")
        lines.append("=" * 18)
        return "\n".join(lines)
    if info.get("ros") is None:
        lines.append(f"状态:     {info.get('error', 'ROS 未启动')}")
        lines.append("=" * 18)
        return "\n".join(lines)
    ros_t = info["ros"]
    lines.append(f"ROS时间:  {ros_t['str']}  (仿真时间: {'是' if ros_t['use_sim_time'] else '否'})")
    lines.append(f"时间差:   {info['diff_sec']} 秒")
    if info.get("clock_topic"):
        lines.append(f"/clock:   {info['clock_topic']['type']}")
    lines.append(f"同步状态: {info.get('sync_status', '未知')}")
    lines.append("=" * 18)
    return "\n".join(lines)


def get_report():
    """供 GUI 调用的报告函数"""
    return format_report()


def plugin_unload():
    """卸载插件时的清理"""
    pass
