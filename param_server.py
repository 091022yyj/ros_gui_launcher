#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数服务器模块
- 可视化查看ROS参数
- 编辑参数值
- 支持参数导入导出
"""
import os
import json
import subprocess
import yaml


class ParameterServer:
    """参数服务器管理器"""

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

    def get_all_params(self):
        """获取所有参数"""
        stdout, stderr, code = self._run_command("rosparam list")
        if code != 0:
            return {"params": [], "error": stderr}

        params = []
        for line in stdout.split("\n"):
            param = line.strip()
            if param:
                params.append(param)

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

    def set_param_value(self, param_name, value):
        """设置参数值"""
        # 转换为YAML格式
        if isinstance(value, dict):
            yaml_value = yaml.dump(value)
        elif isinstance(value, list):
            yaml_value = yaml.dump(value)
        elif isinstance(value, bool):
            yaml_value = "true" if value else "false"
        elif isinstance(value, (int, float)):
            yaml_value = str(value)
        else:
            yaml_value = f"'{value}'"

        cmd = f"rosparam set {param_name} '{yaml_value}'"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "error": stderr}

    def delete_param(self, param_name):
        """删除参数"""
        cmd = f"rosparam delete {param_name}"
        stdout, stderr, code = self._run_command(cmd)
        return {"success": code == 0, "error": stderr}

    def get_param_type(self, param_name):
        """获取参数类型"""
        value_result = self.get_param_value(param_name)
        if value_result["error"]:
            return {"type": "unknown", "error": value_result["error"]}

        value = value_result["value"]
        if isinstance(value, bool):
            return {"type": "bool", "error": None}
        elif isinstance(value, int):
            return {"type": "int", "error": None}
        elif isinstance(value, float):
            return {"type": "float", "error": None}
        elif isinstance(value, list):
            return {"type": "list", "error": None}
        elif isinstance(value, dict):
            return {"type": "dict", "error": None}
        else:
            return {"type": "string", "error": None}

    def export_params(self, output_file, param_prefix=None):
        """导出参数"""
        params_result = self.get_all_params()
        if params_result["error"]:
            return {"success": False, "error": params_result["error"]}

        params = {}
        for param in params_result["params"]:
            if param_prefix and not param.startswith(param_prefix):
                continue

            value_result = self.get_param_value(param)
            if not value_result["error"]:
                params[param] = value_result["value"]

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(params, f, ensure_ascii=False, indent=2)
            return {"success": True, "count": len(params)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_params(self, input_file):
        """导入参数"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                params = json.load(f)

            success_count = 0
            error_count = 0

            for param, value in params.items():
                result = self.set_param_value(param, value)
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

            return {
                "success": True,
                "imported": success_count,
                "errors": error_count
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_param_tree(self):
        """获取参数树结构"""
        params_result = self.get_all_params()
        if params_result["error"]:
            return {"tree": {}, "error": params_result["error"]}

        tree = {}
        for param in params_result["params"]:
            parts = param.strip("/").split("/")
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = param

        return {"tree": tree, "error": None}

    def search_params(self, keyword):
        """搜索参数"""
        params_result = self.get_all_params()
        if params_result["error"]:
            return {"params": [], "error": params_result["error"]}

        matching = []
        for param in params_result["params"]:
            if keyword.lower() in param.lower():
                matching.append(param)

        return {"params": matching, "error": None}
