#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息录制模块
- 录制ROS话题数据到bag文件
- 支持播放bag文件
- 支持查看bag文件信息
"""
import os
import subprocess
import signal
from datetime import datetime


class MessageRecorder:
    """消息录制器"""
    
    def __init__(self, ros_setup="", ws_setup="", bag_dir="bags"):
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.bag_dir = bag_dir
        self.recording_process = None
        self._build_source_cmd()
        self._ensure_bag_dir()
    
    def _build_source_cmd(self):
        """构建source命令"""
        parts = []
        if self.ros_setup and os.path.exists(self.ros_setup):
            parts.append(f"source '{self.ros_setup}'")
        if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
            parts.append(f"source '{os.path.expanduser(self.ws_setup)}'")
        self.source_cmd = " && ".join(parts) if parts else ""
    
    def _ensure_bag_dir(self):
        """确保bag目录存在"""
        if not os.path.exists(self.bag_dir):
            os.makedirs(self.bag_dir, exist_ok=True)
    
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
                timeout=10
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", 1
        except Exception as e:
            return "", str(e), 1
    
    def start_recording(self, topics=None, bag_name=None):
        """开始录制"""
        if self.recording_process:
            return {"success": False, "error": "已在录制中"}
        
        # 生成bag文件名
        if not bag_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bag_name = f"recording_{timestamp}.bag"
        
        bag_path = os.path.join(self.bag_dir, bag_name)
        
        # 构建录制命令
        cmd = f"rosbag record -O {bag_path}"
        if topics:
            if isinstance(topics, str):
                topics = [topics]
            cmd += " " + " ".join(topics)
        else:
            cmd += " -a"  # 录制所有话题
        
        # 启动录制进程
        full_cmd = cmd
        if self.source_cmd:
            full_cmd = f"{self.source_cmd} && {cmd}"
        
        try:
            # 使用 start_new_session=True 创建新进程组，便于后续杀死
            self.recording_process = subprocess.Popen(
                ["bash", "-c", full_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # 创建新会话/进程组
            )
            return {"success": True, "bag_path": bag_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_recording(self):
        """停止录制"""
        if not self.recording_process:
            return {"success": False, "error": "未在录制中"}
        
        try:
            # 获取进程组ID
            pgid = os.getpgid(self.recording_process.pid)
            # 杀死整个进程组
            os.killpg(pgid, signal.SIGINT)
            
            # 等待进程结束
            try:
                self.recording_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 如果还没结束，强制杀死
                os.killpg(pgid, signal.SIGKILL)
                self.recording_process.wait(timeout=2)
            
            self.recording_process = None
            return {"success": True}
        except ProcessLookupError:
            # 进程已经不存在
            self.recording_process = None
            return {"success": True}
        except Exception as e:
            self.recording_process = None
            return {"success": False, "error": str(e)}
    
    def force_stop(self):
        """强制停止录制"""
        if not self.recording_process:
            return {"success": False, "error": "未在录制中"}
        
        try:
            pgid = os.getpgid(self.recording_process.pid)
            os.killpg(pgid, signal.SIGKILL)
            self.recording_process = None
            return {"success": True}
        except:
            self.recording_process = None
            return {"success": True}
    
    def is_recording(self):
        """是否正在录制"""
        if not self.recording_process:
            return False
        return self.recording_process.poll() is None
    
    def get_bag_info(self, bag_path):
        """获取bag文件信息"""
        if not os.path.exists(bag_path):
            return {"error": "文件不存在"}
        
        cmd = f"rosbag info {bag_path}"
        stdout, stderr, code = self._run_command(cmd)
        
        if code != 0:
            return {"error": stderr}
        
        # 解析bag信息
        info = {
            "path": bag_path,
            "size": os.path.getsize(bag_path),
            "duration": None,
            "start_time": None,
            "end_time": None,
            "messages": None,
            "topics": [],
        }
        
        for line in stdout.split("\n"):
            line = line.strip()
            if "duration:" in line:
                try:
                    info["duration"] = float(line.split(":")[-1].strip().replace("s", ""))
                except ValueError:
                    pass
            elif "start:" in line:
                info["start_time"] = line.split(":")[-1].strip()
            elif "end:" in line:
                info["end_time"] = line.split(":")[-1].strip()
            elif "messages:" in line:
                try:
                    info["messages"] = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "topic" in line and ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    info["topics"].append(parts[0].strip())
        
        return {"info": info, "output": stdout}
    
    def play_bag(self, bag_path, rate=1.0):
        """播放bag文件"""
        if not os.path.exists(bag_path):
            return {"success": False, "error": "文件不存在"}
        
        cmd = f"rosbag play {bag_path} -r {rate}"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def get_bag_files(self):
        """获取bag文件列表"""
        if not os.path.exists(self.bag_dir):
            return {"files": []}
        
        files = []
        for f in os.listdir(self.bag_dir):
            if f.endswith(".bag"):
                file_path = os.path.join(self.bag_dir, f)
                files.append({
                    "name": f,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return {"files": sorted(files, key=lambda x: x["modified"], reverse=True)}
    
    def delete_bag(self, bag_path):
        """删除bag文件"""
        if os.path.exists(bag_path):
            try:
                os.remove(bag_path)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "文件不存在"}
    
    def get_recorded_topics(self):
        """获取可录制的话题列表"""
        cmd = "rostopic list"
        stdout, stderr, code = self._run_command(cmd)
        
        if code != 0:
            return {"topics": [], "error": stderr}
        
        topics = [t.strip() for t in stdout.split("\n") if t.strip()]
        return {"topics": topics, "error": None}
