#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿真控制模块
- 控制Gazebo仿真
- 暂停、重启、步进
"""
import os
import subprocess
import signal


class SimulationController:
    """仿真控制器"""
    
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
                timeout=10
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", 1
        except Exception as e:
            return "", str(e), 1
    
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
