#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TF树监控模块
- 查看TF变换关系
- 显示坐标系树结构
- 检查TF延迟和异常
"""
import os
import subprocess
import re
from collections import defaultdict


class TFMonitor:
    """TF监控器"""

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

    def _run_command(self, cmd, timeout=10):
        """运行ROS命令"""
        full_cmd = cmd
        if self.source_cmd:
            full_cmd = f"{self.source_cmd} && {cmd}"

        try:
            result = subprocess.run(
                ["bash", "-c", full_cmd],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", 1
        except Exception as e:
            return "", str(e), 1

    def get_tf_tree(self):
        """获取TF树结构"""
        cmd = "rosrun tf view_frames"
        stdout, stderr, code = self._run_command(cmd)

        if code != 0:
            return {"error": stderr}

        # 查找生成的PDF文件
        pdf_path = os.path.join(os.getcwd(), "frames.pdf")
        if os.path.exists(pdf_path):
            return {"pdf_path": pdf_path, "output": stdout}

        return {"output": stdout, "pdf_path": None}

    def get_tf_topics(self):
        """获取TF相关话题"""
        cmd = "rostopic list | grep tf"
        stdout, stderr, code = self._run_command(cmd)

        if code != 0:
            return {"topics": [], "error": stderr}

        topics = [t.strip() for t in stdout.split("\n") if t.strip()]
        return {"topics": topics, "error": None}

    def get_tf_message_info(self, topic="/tf"):
        """获取TF消息信息"""
        cmd = f"rostopic info {topic}"
        stdout, stderr, code = self._run_command(cmd)

        if code != 0:
            return {"error": stderr}

        info = {
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

    def get_tf_frames(self):
        """获取所有TF坐标系(用rostopic快速获取,不用永不退出的tf_monitor)"""
        cmd = "rostopic echo /tf -n 1 2>/dev/null"
        stdout, stderr, code = self._run_command(cmd, timeout=5)
        if code != 0:
            # 备用: 静态TF
            cmd = "rostopic echo /tf_static -n 1 2>/dev/null"
            stdout, stderr, code = self._run_command(cmd, timeout=5)
            if code != 0:
                return {"frames": [], "error": stderr or "未获取到TF数据"}

        # 解析坐标系
        frames = set()
        for line in stdout.split("\n"):
            match = re.search(r'frame_id:\s*["\']?(\w+)["\']?', line)
            if match:
                frames.add(match.group(1))
            match = re.search(r'child_frame_id:\s*["\']?(\w+)["\']?', line)
            if match:
                frames.add(match.group(1))

        return {"frames": sorted(list(frames)), "error": None}

    def get_tf_transform(self, target_frame, source_frame):
        """获取两个坐标系之间的变换"""
        cmd = f"rosrun tf tf_echo {target_frame} {source_frame}"
        stdout, stderr, code = self._run_command(cmd)

        if code != 0:
            return {"error": stderr}

        # 解析变换信息
        transform = {
            "translation": {"x": 0, "y": 0, "z": 0},
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
        }

        for line in stdout.split("\n"):
            # 解析平移
            trans_match = re.search(r'Translation:\s*\[([^\]]+)\]', line)
            if trans_match:
                values = trans_match.group(1).split(",")
                if len(values) >= 3:
                    transform["translation"]["x"] = float(values[0].strip())
                    transform["translation"]["y"] = float(values[1].strip())
                    transform["translation"]["z"] = float(values[2].strip())

            # 解析旋转
            rot_match = re.search(r'Rotation:\s*\[([^\]]+)\]', line)
            if rot_match:
                values = rot_match.group(1).split(",")
                if len(values) >= 4:
                    transform["rotation"]["x"] = float(values[0].strip())
                    transform["rotation"]["y"] = float(values[1].strip())
                    transform["rotation"]["z"] = float(values[2].strip())
                    transform["rotation"]["w"] = float(values[3].strip())

        return {"transform": transform, "output": stdout}

    def get_tf_delay(self, target_frame, source_frame):
        """获取TF延迟"""
        cmd = f"rosrun tf tf_monitor {target_frame} {source_frame}"
        stdout, stderr, code = self._run_command(cmd)

        if code != 0:
            return {"error": stderr}

        # 解析延迟信息
        delay = None
        for line in stdout.split("\n"):
            match = re.search(r'Average Delay:\s*([0-9.]+)', line)
            if match:
                delay = float(match.group(1))
                break

        return {"delay": delay, "output": stdout}

    def check_tf_health(self):
        """检查TF健康状态"""
        health = {
            "topics_exist": False,
            "publishers_exist": False,
            "frames_exist": False,
            "issues": [],
        }

        # 检查TF话题
        topics_result = self.get_tf_topics()
        if topics_result["topics"]:
            health["topics_exist"] = True
        else:
            health["issues"].append("未发现TF话题")

        # 检查发布者
        info_result = self.get_tf_message_info()
        if not info_result.get("error") and info_result.get("info", {}).get("publishers"):
            health["publishers_exist"] = True
        else:
            health["issues"].append("未发现TF发布者")

        # 检查坐标系
        frames_result = self.get_tf_frames()
        if frames_result["frames"]:
            health["frames_exist"] = True
            health["frame_count"] = len(frames_result["frames"])
        else:
            health["issues"].append("未发现TF坐标系")

        health["healthy"] = all([
            health["topics_exist"],
            health["publishers_exist"],
            health["frames_exist"]
        ])

        return health

    def visualize_tf_tree(self):
        """可视化TF树（打开PDF）"""
        result = self.get_tf_tree()
        if result.get("pdf_path"):
            try:
                import webbrowser
                webbrowser.open(f"file://{result['pdf_path']}")
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "无法生成TF树PDF"}
