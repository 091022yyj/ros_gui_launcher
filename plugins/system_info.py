#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置插件: 系统信息
- 显示 IP 地址、磁盘剩余、CPU 型号、内存/负载等信息
"""
import os
import socket
import platform
import subprocess

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def plugin_info():
    """插件元数据"""
    return {
        "name": "系统信息",
        "description": "显示 IP 地址、磁盘剩余空间、CPU 型号等系统信息",
        "version": "1.0.0",
        "author": "内置",
        "homepage": "",
    }


def _get_ip_addresses():
    """获取本机所有 IPv4 地址"""
    ips = []
    if _HAS_PSUTIL:
        try:
            for ifname, addrs in psutil.net_if_addrs().items():
                if ifname.startswith(("lo", "docker", "veth", "br-", "virbr")):
                    continue
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        if ip not in ips and not ip.startswith("127."):
                            ips.append(ip)
        except (AttributeError, OSError):
            pass
    if not ips:
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                addr = info[4][0]
                if addr not in ips and not addr.startswith("127."):
                    ips.append(addr)
        except OSError:
            pass
    return ips


def _get_disk_usage():
    """获取根分区与家目录分区剩余空间"""
    disks = []
    seen = set()
    for path in ["/", os.path.expanduser("~")]:
        try:
            usage = psutil.disk_usage(path)
        except (OSError, AttributeError):
            continue
        if usage.device in seen:
            continue
        seen.add(usage.device)
        disks.append({
            "mount": path,
            "total_gb": round(usage.total / 1024 ** 3, 1),
            "free_gb": round(usage.free / 1024 ** 3, 1),
            "percent": usage.percent,
        })
    return disks


def _get_cpu_model():
    """获取 CPU 型号"""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "未知"


def get_system_info():
    """获取系统信息"""
    info = {
        "hostname": socket.gethostname(),
        "os": platform.system() + " " + platform.release(),
        "python": platform.python_version(),
        "cpu_model": _get_cpu_model(),
        "cpu_count": os.cpu_count() or 0,
        "ip_addresses": _get_ip_addresses(),
    }
    if _HAS_PSUTIL:
        try:
            mem = psutil.virtual_memory()
            info["memory"] = {
                "total_gb": round(mem.total / 1024 ** 3, 1),
                "used_gb": round(mem.used / 1024 ** 3, 1),
                "percent": mem.percent,
            }
            info["load_avg"] = [round(x, 2) for x in os.getloadavg()]
        except (AttributeError, OSError):
            pass
        try:
            info["disks"] = _get_disk_usage()
        except AttributeError:
            pass
    return info


def format_report():
    """生成可读的系统信息报告文本"""
    info = get_system_info()
    lines = [
        "===== 系统信息 =====",
        f"主机名:   {info['hostname']}",
        f"操作系统: {info['os']}",
        f"Python:   {info['python']}",
        f"CPU型号:  {info['cpu_model']}",
        f"CPU核数:  {info['cpu_count']}",
        f"IP地址:   {', '.join(info.get('ip_addresses') or ['(无)'])}",
    ]
    if "memory" in info:
        mem = info["memory"]
        lines.append(f"内存:     {mem['used_gb']}GB / {mem['total_gb']}GB ({mem['percent']}%)")
    if "load_avg" in info:
        lines.append(f"负载:     {info['load_avg']}")
    if "disks" in info:
        for disk in info["disks"]:
            lines.append(
                f"磁盘[{disk['mount']}]: {disk['free_gb']}GB 空闲 / "
                f"{disk['total_gb']}GB 总量 ({disk['percent']}%)"
            )
    lines.append("=" * 18)
    return "\n".join(lines)


def get_report():
    """供 GUI 调用的报告函数"""
    return format_report()


def plugin_unload():
    """卸载插件时的清理"""
    pass
