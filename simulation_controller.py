#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿真控制模块
- 控制Gazebo仿真(暂停/继续/重置/步进)
- 一键启动/停止Gazebo环境
- 加载机器人模型(URDF/SDF)
- 仿真场景预设启动
"""
import os
import subprocess
import signal


class SimulationController:
    """仿真控制器"""
    
    def __init__(self, ros_setup="", ws_setup=""):
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.gazebo_process = None
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
    
    def pause_simulation(self):
        """暂停仿真"""
        cmd = "rosservice call /gazebo/pause_physics"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def unpause_simulation(self):
        """继续仿真"""
        cmd = "rosservice call /gazebo/unpause_physics"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def reset_simulation(self):
        """重置仿真"""
        cmd = "rosservice call /gazebo/reset_simulation"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def get_simulation_state(self):
        """获取仿真状态"""
        cmd = "rosservice call /gazebo/get_world_properties"
        stdout, stderr, code = self._run_command(cmd)
        
        if code != 0:
            return {"running": False, "error": stderr}
        
        # 检查是否在运行
        running = "paused: False" in stdout or "paused: true" in stdout
        paused = "paused: True" in stdout or "paused: true" in stdout
        
        return {
            "running": running,
            "paused": paused,
            "output": stdout,
            "error": None
        }
    
    def step_simulation(self, steps=1):
        """步进仿真"""
        cmd = f"rosservice call /gazebo/set_physics_properties {{time_step: 0.001, max_update_rate: 1000.0}}"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def spawn_model(self, model_name, x=0, y=0, z=0, roll=0, pitch=0, yaw=0):
        """生成模型"""
        cmd = f"""rosservice call /gazebo/spawn_sdf_model \
            "{model_name}" \
            "name: '{model_name}'" \
            "''" \
            "namespace: ''" \
            "pose:" \
            "  position:" \
            "    x: {x}" \
            "    y: {y}" \
            "    z: {z}" \
            "  orientation:" \
            "    x: {roll}" \
            "    y: {pitch}" \
            "    z: {yaw}" \
            "    w: 1.0" \
            "reference_frame: 'world'" """
        
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def delete_model(self, model_name):
        """删除模型"""
        cmd = f"rosservice call /gazebo/delete_model {{model_name: '{model_name}'}}"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def get_world_properties(self):
        """获取世界属性"""
        cmd = "rosservice call /gazebo/get_world_properties"
        stdout, stderr, code = self._run_command(cmd)
        return {"output": stdout, "error": stderr if code != 0 else None}
    
    def get_physics_properties(self):
        """获取物理属性"""
        cmd = "rosservice call /gazebo/get_physics_properties"
        stdout, stderr, code = self._run_command(cmd)
        return {"output": stdout, "error": stderr if code != 0 else None}
    
    def set_physics_properties(self, time_step=0.001, max_update_rate=1000.0):
        """设置物理属性"""
        cmd = f"rosservice call /gazebo/set_physics_properties {{time_step: {time_step}, max_update_rate: {max_update_rate}}}"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    # ========== Gazebo环境启动/停止 ==========

    def start_gazebo(self, world_path=""):
        """启动Gazebo(后台进程)
        world_path: 世界文件路径(空=empty_world)
        """
        if self.gazebo_process and self.gazebo_process.poll() is None:
            return {"success": False, "error": "Gazebo已在运行"}
        
        if world_path:
            cmd = f"roslaunch gazebo_ros empty_world.launch world_name:={world_path}"
        else:
            cmd = "roslaunch gazebo_ros empty_world.launch"
        
        full_cmd = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        
        try:
            self.gazebo_process = subprocess.Popen(
                ["bash", "-c", full_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_gazebo_world(self, world_path):
        """启动指定世界文件的Gazebo"""
        return self.start_gazebo(world_path)
    
    def stop_gazebo(self):
        """停止Gazebo"""
        if self.gazebo_process:
            try:
                pgid = os.getpgid(self.gazebo_process.pid)
                os.killpg(pgid, signal.SIGTERM)
                try:
                    self.gazebo_process.wait(timeout=5)
                except Exception:
                    os.killpg(pgid, signal.SIGKILL)
            except Exception:
                pass
            self.gazebo_process = None
        # 保险: 杀掉残留的gazebo进程
        self._run_command("pkill -f 'gazebo' 2>/dev/null; pkill -f 'gzserver' 2>/dev/null", timeout=3)
        return {"success": True}
    
    def is_gazebo_running(self):
        """Gazebo是否在运行"""
        if self.gazebo_process and self.gazebo_process.poll() is None:
            return True
        # 检查进程
        stdout, _, code = self._run_command("pgrep -f gzserver | head -1", timeout=3)
        return code == 0 and bool(stdout.strip())
    
    def get_gazebo_models(self):
        """获取当前世界中的模型列表"""
        stdout, stderr, code = self._run_command(
            "rosservice call /gazebo/get_world_properties 2>/dev/null | grep 'model_names' -A 20",
            timeout=5)
        if code != 0:
            return {"models": [], "error": stderr}
        models = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("model_names") and not line.startswith("-"):
                models.append(line.replace("-", "").strip())
            elif line.startswith("- "):
                models.append(line[2:].strip())
        return {"models": [m for m in models if m], "error": None}
    
    # ========== 模型加载 ==========

    def spawn_urdf_model(self, urdf_path, model_name="robot", x=0, y=0, z=0.1, yaw=0):
        """加载URDF模型到Gazebo
        urdf_path: URDF文件路径
        """
        if not os.path.exists(urdf_path):
            return {"success": False, "error": f"URDF文件不存在: {urdf_path}"}
        
        cmd = f"""rosrun gazebo_ros spawn_model -file '{urdf_path}' \
            -urdf -model {model_name} -x {x} -y {y} -z {z} -Y {yaw}"""
        stdout, stderr, code = self._run_command(cmd, timeout=15)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    def spawn_sdf_model(self, sdf_path, model_name="robot", x=0, y=0, z=0.1, yaw=0):
        """加载SDF模型到Gazebo"""
        if not os.path.exists(sdf_path):
            return {"success": False, "error": f"SDF文件不存在: {sdf_path}"}
        
        cmd = f"""rosrun gazebo_ros spawn_model -file '{sdf_path}' \
            -sdf -model {model_name} -x {x} -y {y} -z {z} -Y {yaw}"""
        stdout, stderr, code = self._run_command(cmd, timeout=15)
        return {"success": code == 0, "output": stdout, "error": stderr}
    
    # ========== 仿真场景 ==========

    def start_simulation_scene(self, launch_pkg, launch_file, extra_args=""):
        """通过roslaunch启动完整仿真场景(如turtlebot3_world)
        launch_pkg: 功能包名, launch_file: launch文件名
        """
        cmd = f"roslaunch {launch_pkg} {launch_file}"
        if extra_args:
            cmd += f" {extra_args}"
        
        full_cmd = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        
        try:
            self.gazebo_process = subprocess.Popen(
                ["bash", "-c", full_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_common_scenes(self):
        """获取常见仿真场景(检测工作空间中的仿真包)"""
        scenes = [
            {"name": "空世界 (empty_world)", "pkg": "gazebo_ros",
             "file": "empty_world.launch", "args": ""},
        ]
        # 检测工作空间中的常见仿真包
        ws = ""
        if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
            ws = os.path.dirname(os.path.dirname(os.path.expanduser(self.ws_setup)))
            src = os.path.join(ws, "src")
            if os.path.exists(src):
                for pkg in ("turtlebot3_gazebo", "wpr_simulation", "turtlebot3_simulations",
                            "gazebo_ros_pkgs", "robot_sim"):
                    pkg_path = os.path.join(src, pkg)
                    if os.path.exists(pkg_path):
                        launch_dir = os.path.join(pkg_path, "launch")
                        if os.path.exists(launch_dir):
                            for f in os.listdir(launch_dir):
                                if f.endswith(".launch") and not f.startswith("."):
                                    scenes.append({
                                        "name": f"{pkg}/{f}",
                                        "pkg": pkg,
                                        "file": f,
                                        "args": ""
                                    })
        return scenes
    
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
