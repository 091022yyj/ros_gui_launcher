#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多机协同模块 - 增强版
- 通过SSH控制远程ROS节点
- 支持远程启动launch文件
- 支持远程查看机器人状态
- 密码安全存储
- 实时终端执行
"""
import os
import subprocess
import json
import base64
import threading
import queue


class MultiMachineController:
    """多机协同控制器"""
    
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or os.path.dirname(__file__)
        self.machines_file = os.path.join(self.config_dir, "machines.json")
        self.machines = {}
        self._load_machines()
    
    def _load_machines(self):
        """加载机器配置"""
        if os.path.exists(self.machines_file):
            try:
                with open(self.machines_file, "r", encoding="utf-8") as f:
                    self.machines = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.machines = {}
        else:
            self.machines = {}
    
    def save_machines(self):
        """保存机器配置"""
        try:
            with open(self.machines_file, "w", encoding="utf-8") as f:
                json.dump(self.machines, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
    
    def add_machine(self, name, hostname, username, port=22, password=None, ros_setup=None):
        """添加机器"""
        machine = {
            "name": name,
            "hostname": hostname,
            "username": username,
            "port": port,
            "password": self._encode_password(password) if password else None,
            "ros_setup": ros_setup or "source ~/.bashrc",
            "connected": False,
            "launch_process": None,
        }
        self.machines[name] = machine
        self.save_machines()
        return machine
    
    def _encode_password(self, password):
        """简单编码密码（不是加密，仅混淆）"""
        return base64.b64encode(password.encode()).decode()
    
    def _decode_password(self, encoded):
        """解码密码"""
        if not encoded:
            return None
        try:
            return base64.b64decode(encoded.encode()).decode()
        except:
            return None
    
    def remove_machine(self, name):
        """移除机器"""
        if name in self.machines:
            del self.machines[name]
            self.save_machines()
            return True
        return False
    
    def get_machine(self, name):
        """获取机器"""
        return self.machines.get(name)
    
    def get_all_machines(self):
        """获取所有机器"""
        return self.machines
    
    def get_machine_list(self):
        """获取机器列表"""
        machines = []
        for name, machine in self.machines.items():
            machines.append({
                "name": name,
                "hostname": machine.get("hostname", ""),
                "username": machine.get("username", ""),
                "port": machine.get("port", 22),
                "ros_setup": machine.get("ros_setup", "source ~/.bashrc"),
                "connected": machine.get("connected", False),
            })
        return machines
    
    def _build_ssh_command(self, machine_name, command, use_password=False):
        """构建SSH命令"""
        machine = self.machines.get(machine_name)
        if not machine:
            return None
        
        hostname = machine.get("hostname", "")
        username = machine.get("username", "")
        port = machine.get("port", 22)
        
        # 使用 sshpass 处理密码
        if use_password:
            password = self._decode_password(machine.get("password"))
            if password:
                sshpass_cmd = f"sshpass -p '{password}' "
            else:
                sshpass_cmd = ""
        else:
            sshpass_cmd = ""
        
        # 构建完整的ROS环境命令
        ros_setup = machine.get("ros_setup", "source ~/.bashrc")
        full_cmd = f"{ros_setup} && {command}"
        
        ssh_cmd = f"{sshpass_cmd}ssh -o StrictHostKeyChecking=no -p {port} {username}@{hostname} '{full_cmd}'"
        return ssh_cmd
    
    def _run_ssh_command(self, machine_name, command, use_password=True, timeout=30):
        """通过SSH运行命令"""
        ssh_cmd = self._build_ssh_command(machine_name, command, use_password)
        if not ssh_cmd:
            return {"success": False, "error": "机器不存在"}
        
        try:
            result = subprocess.run(
                ssh_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "SSH连接超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_connection(self, machine_name):
        """测试SSH连接"""
        result = self._run_ssh_command(machine_name, "echo 'connected'")
        if result["success"]:
            self.machines[machine_name]["connected"] = True
        else:
            self.machines[machine_name]["connected"] = False
        self.save_machines()
        return result
    
    def setup_ssh_key(self, machine_name):
        """设置SSH密钥（免密登录）"""
        machine = self.machines.get(machine_name)
        if not machine:
            return {"success": False, "error": "机器不存在"}
        
        hostname = machine.get("hostname", "")
        username = machine.get("username", "")
        port = machine.get("port", 22)
        password = self._decode_password(machine.get("password"))
        
        # 生成密钥（如果不存在）
        key_path = os.path.expanduser("~/.ssh/id_rsa")
        if not os.path.exists(key_path):
            subprocess.run(["ssh-keygen", "-t", "rsa", "-N", "", "-f", key_path], 
                         capture_output=True)
        
        # 使用sshpass复制公钥到远程机器
        if password:
            try:
                pub_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
                if os.path.exists(pub_key_path):
                    with open(pub_key_path, "r") as f:
                        pub_key = f.read().strip()
                    
                    cmd = f"echo '{pub_key}' >> ~/.ssh/authorized_keys"
                    result = self._run_ssh_command(machine_name, cmd, use_password=True)
                    if result["success"]:
                        return {"success": True, "message": "SSH密钥已设置"}
                    return result
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": "请先设置密码"}
    
    # ========== ROS远程控制功能 ==========
    
    def start_ros_master(self, machine_name):
        """在远程机器启动roscore"""
        cmd = "roscore &"
        return self._run_ssh_command(machine_name, cmd, timeout=10)
    
    def stop_ros_master(self, machine_name):
        """在远程机器停止roscore"""
        cmd = "rosnode kill /rosout"
        return self._run_ssh_command(machine_name, cmd)
    
    def start_launch_file(self, machine_name, launch_file):
        """在远程机器启动launch文件"""
        cmd = f"roslaunch {launch_file} &"
        result = self._run_ssh_command(machine_name, cmd, timeout=5)
        return result
    
    def start_launch_file_background(self, machine_name, launch_file):
        """在后台启动launch文件"""
        cmd = f"nohup roslaunch {launch_file} > /tmp/launch.log 2>&1 &"
        result = self._run_ssh_command(machine_name, cmd, timeout=5)
        return result
    
    def stop_launch_process(self, machine_name):
        """停止launch进程"""
        cmd = "pkill -f roslaunch"
        return self._run_ssh_command(machine_name, cmd)
    
    def get_ros_nodes(self, machine_name):
        """获取远程机器的ROS节点"""
        cmd = "rosnode list"
        result = self._run_ssh_command(machine_name, cmd)
        if result["success"]:
            nodes = [n.strip() for n in result["output"].split("\n") if n.strip()]
            return {"nodes": nodes, "error": None}
        return {"nodes": [], "error": result["error"]}
    
    def get_ros_topics(self, machine_name):
        """获取远程机器的ROS话题"""
        cmd = "rostopic list"
        result = self._run_ssh_command(machine_name, cmd)
        if result["success"]:
            topics = [t.strip() for t in result["output"].split("\n") if t.strip()]
            return {"topics": topics, "error": None}
        return {"topics": [], "error": result["error"]}
    
    def get_topic_info(self, machine_name, topic_name):
        """获取话题信息"""
        cmd = f"rostopic info {topic_name}"
        return self._run_ssh_command(machine_name, cmd)
    
    def get_topic_hz(self, machine_name, topic_name):
        """获取话题发布频率"""
        cmd = f"rostopic hz {topic_name} -w 2"
        return self._run_ssh_command(machine_name, cmd, timeout=5)
    
    def publish_topic(self, machine_name, topic_name, msg_type, message):
        """发布话题消息"""
        cmd = f"rostopic pub -1 {topic_name} {msg_type} \"{message}\""
        return self._run_ssh_command(machine_name, cmd, timeout=5)
    
    def get_ros_services(self, machine_name):
        """获取远程机器的ROS服务"""
        cmd = "rosservice list"
        result = self._run_ssh_command(machine_name, cmd)
        if result["success"]:
            services = [s.strip() for s in result["output"].split("\n") if s.strip()]
            return {"services": services, "error": None}
        return {"services": [], "error": result["error"]}
    
    def call_ros_service(self, machine_name, service_name, args=""):
        """调用ROS服务"""
        if args:
            cmd = f"rosservice call {service_name} \"{args}\""
        else:
            cmd = f"rosservice call {service_name}"
        return self._run_ssh_command(machine_name, cmd, timeout=10)
    
    def get_robot_status(self, machine_name):
        """获取机器人状态"""
        status = {}
        
        # 获取节点
        nodes_result = self.get_ros_nodes(machine_name)
        status["nodes"] = nodes_result.get("nodes", [])
        
        # 获取话题
        topics_result = self.get_ros_topics(machine_name)
        status["topics"] = topics_result.get("topics", [])
        
        # 获取系统信息
        cpu_result = self._run_ssh_command(machine_name, "cat /proc/cpuinfo | grep 'model name' | head -1")
        status["cpu"] = cpu_result.get("output", "未知")
        
        mem_result = self._run_ssh_command(machine_name, "free -m | awk 'NR==2{printf \"%d%%\", $3*100/$2}'")
        status["memory"] = mem_result.get("output", "未知")
        
        disk_result = self._run_ssh_command(machine_name, "df -h / | awk 'NR==2{print $5}'")
        status["disk"] = disk_result.get("output", "未知")
        
        uptime_result = self._run_ssh_command(machine_name, "uptime -p")
        status["uptime"] = uptime_result.get("output", "未知")
        
        return status
    
    def get_ros_environment(self, machine_name):
        """获取远程ROS环境变量"""
        env_vars = {}
        
        for var in ["ROS_MASTER_URI", "ROS_IP", "ROS_HOSTNAME", "ROS_NAMESPACE"]:
            result = self._run_ssh_command(machine_name, f"echo ${var}")
            if result["success"] and result["output"]:
                env_vars[var] = result["output"]
        
        return env_vars
    
    def set_ros_master_uri(self, machine_name, master_uri):
        """设置远程ROS_MASTER_URI"""
        cmd = f"export ROS_MASTER_URI={master_uri} && echo $ROS_MASTER_URI"
        return self._run_ssh_command(machine_name, cmd)
    
    def record_rosbag(self, machine_name, output_path, duration=None, topics=None):
        """远程录制rosbag"""
        cmd = "rosbag record -O {output}".format(output=output_path)
        if topics:
            cmd += f" {' '.join(topics)}"
        else:
            cmd += " -a"
        if duration:
            cmd += f" --duration={duration}"
        cmd += " &"
        return self._run_ssh_command(machine_name, cmd, timeout=5)
    
    def stop_rosbag(self, machine_name):
        """停止录制rosbag"""
        cmd = "pkill -f rosbag"
        return self._run_ssh_command(machine_name, cmd)
    
    def execute_remote_command(self, machine_name, command, callback=None):
        """执行远程命令并返回实时输出（非阻塞）"""
        ssh_cmd = self._build_ssh_command(machine_name, command, use_password=True)
        if not ssh_cmd:
            return {"success": False, "error": "机器不存在"}
        
        result_queue = queue.Queue()
        
        def run_in_thread():
            try:
                process = subprocess.Popen(
                    ssh_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate(timeout=60)
                result_queue.put({
                    "success": process.returncode == 0,
                    "output": stdout,
                    "error": stderr if process.returncode != 0 else None
                })
            except subprocess.TimeoutExpired:
                process.kill()
                result_queue.put({"success": False, "error": "执行超时"})
            except Exception as e:
                result_queue.put({"success": False, "error": str(e)})
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        try:
            return result_queue.get(timeout=60)
        except queue.Empty:
            return {"success": False, "error": "等待超时"}
