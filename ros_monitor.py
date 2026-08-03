#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS监控模块
- ROS节点监控
- Topic监控
- 网络监控
- 磁盘监控
"""
import os
import subprocess
import json
import socket
import time
from datetime import datetime


class ROSMonitor:
    """ROS监控器"""

    def __init__(self, ros_setup="", ws_setup=""):
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()

    def _build_source_cmd(self):
        """构建source命令"""
        parts = []
        if self.ros_setup and os.path.exists(self.ros_setup):
            parts.append(f"source '{self.ros_setup}'")
        if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
            parts.append(f"source '{os.path.expanduser(self.ws_setup)}'")
        self.source_cmd = " && ".join(parts) if parts else ""

    def set_ros_env(self, ros_setup, ws_setup):
        """设置ROS环境"""
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()

    def _run_command(self, cmd):
        """运行ROS命令"""
        full_cmd = cmd
        if self.source_cmd:
            full_cmd = f"{self.source_cmd} && {cmd}"

        try:
            result = subprocess.run(
                ["bash", "-c", full_cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", 1
        except Exception as e:
            return "", str(e), 1

    # ========== ROS节点监控 ==========

    def get_ros_nodes(self):
        """获取ROS节点列表"""
        stdout, stderr, code = self._run_command("rosnode list")
        if code != 0:
            return {"nodes": [], "error": stderr}

        nodes = [n.strip() for n in stdout.split("\n") if n.strip()]
        return {"nodes": nodes, "error": None}

    def get_node_info(self, node_name):
        """获取节点信息"""
        stdout, stderr, code = self._run_command(f"rosnode info {node_name}")
        if code != 0:
            return {"info": "", "error": stderr}

        # 解析节点信息
        info = {
            "name": node_name,
            "publishers": [],
            "subscribers": [],
            "services": [],
            "pid": None,
            "connections": [],
        }

        current_section = None
        for line in stdout.split("\n"):
            line = line.strip()
            if "Publishers:" in line:
                current_section = "publishers"
            elif "Subscribers:" in line:
                current_section = "subscribers"
            elif "Services:" in line:
                current_section = "services"
            elif "Pid:" in line:
                try:
                    info["pid"] = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif current_section and line and not line.startswith("-"):
                if current_section == "publishers":
                    info["publishers"].append(line)
                elif current_section == "subscribers":
                    info["subscribers"].append(line)
                elif current_section == "services":
                    info["services"].append(line)

        return {"info": info, "error": None}

    def check_node_alive(self, node_name):
        """检查节点是否存活"""
        stdout, stderr, code = self._run_command(f"rosnode ping {node_name} -c 1 -t 2")
        return code == 0

    # ========== Topic监控 ==========

    def get_ros_topics(self):
        """获取ROS话题列表"""
        stdout, stderr, code = self._run_command("rostopic list")
        if code != 0:
            return {"topics": [], "error": stderr}

        topics = [t.strip() for t in stdout.split("\n") if t.strip()]
        return {"topics": topics, "error": None}

    def get_topic_info(self, topic_name):
        """获取话题信息"""
        stdout, stderr, code = self._run_command(f"rostopic info {topic_name}")
        if code != 0:
            return {"info": "", "error": stderr}

        info = {
            "name": topic_name,
            "type": None,
            "publishers": [],
            "subscribers": [],
        }

        current_section = None
        for line in stdout.split("\n"):
            line = line.strip()
            if "Type:" in line:
                info["type"] = line.split("Type:")[-1].strip()
            elif "Publishers:" in line:
                current_section = "publishers"
            elif "Subscribers:" in line:
                current_section = "subscribers"
            elif current_section and line:
                if line.startswith("*"):
                    line = line[1:].strip()
                if current_section == "publishers":
                    info["publishers"].append(line)
                elif current_section == "subscribers":
                    info["subscribers"].append(line)

        return {"info": info, "error": None}

    def get_topic_frequency(self, topic_name, duration=1.0):
        """获取话题发布频率"""
        stdout, stderr, code = self._run_command(
            f"rostopic hz {topic_name} -w 1"
        )

        # 解析频率信息
        for line in stdout.split("\n"):
            if "average rate" in line:
                try:
                    freq = float(line.split(":")[-1].strip())
                    return {"frequency": freq, "error": None}
                except ValueError:
                    pass

        return {"frequency": 0, "error": "无法获取频率"}

    def get_topic_bandwidth(self, topic_name):
        """获取话题带宽"""
        stdout, stderr, code = self._run_command(
            f"rostopic bw {topic_name} -w 1"
        )

        for line in stdout.split("\n"):
            if "average:" in line:
                try:
                    bw = line.split("average:")[-1].strip()
                    return {"bandwidth": bw, "error": None}
                except ValueError:
                    pass

        return {"bandwidth": "N/A", "error": "无法获取带宽"}

    # ========== 网络监控 ==========

    def check_ros_master(self):
        """检查ROS主节点状态"""
        stdout, stderr, code = self._run_command("rostopic list")
        return {
            "running": code == 0,
            "error": stderr if code != 0 else None
        }

    def get_ros_master_uri(self):
        """获取ROS_MASTER_URI"""
        return os.environ.get("ROS_MASTER_URI", "http://localhost:11311")

    def check_port_open(self, host, port, timeout=2):
        """检查端口是否开放"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_network_connections(self):
        """获取网络连接信息"""
        stdout, stderr, code = self._run_command("netstat -tuln 2>/dev/null || ss -tuln")
        if code != 0:
            return {"connections": [], "error": stderr}

        connections = []
        for line in stdout.split("\n"):
            if "LISTEN" in line or "ESTABLISHED" in line:
                connections.append(line.strip())

        return {"connections": connections, "error": None}

    # ========== 磁盘监控 ==========

    def get_disk_usage(self):
        """获取磁盘使用情况"""
        try:
            import psutil
            partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                    })
                except PermissionError:
                    continue
            return {"partitions": partitions, "error": None}
        except ImportError:
            return self._get_disk_usage_fallback()

    def _get_disk_usage_fallback(self):
        """备用磁盘使用获取方法"""
        try:
            result = subprocess.run(
                ["df", "-h"],
                capture_output=True,
                text=True,
                timeout=5
            )
            partitions = []
            for line in result.stdout.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    partitions.append({
                        "device": parts[0],
                        "mountpoint": parts[5],
                        "size": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "percent": parts[4],
                    })
            return {"partitions": partitions, "error": None}
        except Exception as e:
            return {"partitions": [], "error": str(e)}

    def get_log_directory_size(self, log_dir="logs"):
        """获取日志目录大小"""
        if not os.path.exists(log_dir):
            return {"size": 0, "size_human": "0 B"}

        total_size = 0
        for dirpath, dirnames, filenames in os.walk(log_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass

        return {
            "size": total_size,
            "size_human": self._format_size(total_size)
        }

    def _format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    # ========== ROS服务监控 ==========

    def get_ros_services(self):
        """获取ROS服务列表"""
        stdout, stderr, code = self._run_command("rosservice list")
        if code != 0:
            return {"services": [], "error": stderr}

        services = [s.strip() for s in stdout.split("\n") if s.strip()]
        return {"services": services, "error": None}

    def get_service_info(self, service_name):
        """获取服务信息"""
        stdout, stderr, code = self._run_command(f"rosservice info {service_name}")
        if code != 0:
            return {"info": "", "error": stderr}

        return {"info": stdout, "error": None}

    # ========== ROS参数监控 ==========

    def get_ros_params(self):
        """获取ROS参数列表"""
        stdout, stderr, code = self._run_command("rosparam list")
        if code != 0:
            return {"params": [], "error": stderr}

        params = [p.strip() for p in stdout.split("\n") if p.strip()]
        return {"params": params, "error": None}

    def get_param_value(self, param_name):
        """获取参数值"""
        stdout, stderr, code = self._run_command(f"rosparam get {param_name}")
        if code != 0:
            return {"value": None, "error": stderr}

        try:
            value = json.loads(stdout)
        except json.JSONDecodeError:
            value = stdout

        return {"value": value, "error": None}
