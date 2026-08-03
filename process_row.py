#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProcessRow: 管理一行任务(路径+参数+QProcess进程)
- launch/py任务启动/停止/自动重启
- 支持Windows/Linux
"""
import os
import signal
import platform
from PyQt5.QtCore import QProcess


class ProcessRow:
    """管理一行任务:路径 + 参数 + QProcess 进程"""

    def __init__(self, path, kind, args="", auto_restart=False, auto_start=False):
        self.path = path
        self.kind = kind  # "launch" 或 "py"
        self.args = args
        self.auto_restart = auto_restart
        self.auto_start = auto_start
        self.process = None
        self.stop_requested = False
        self.restart_count = 0

    def _py_interpreter(self):
        """读取 py 文件首行的 shebang,优先使用其中指定的解释器(如 conda 环境的 python)"""
        try:
            with open(self.path, "rb") as f:
                first = f.readline().decode("utf-8", errors="replace").strip()
            if first.startswith("#!"):
                parts = first[2:].strip().split()
                # 处理 #!/usr/bin/env python3 形式
                if parts and parts[0].endswith("env") and len(parts) > 1:
                    return parts[1]
                if parts:
                    return parts[0]
        except OSError:
            pass
        return "python3"

    def build_command(self, ros_setup, ws_setup):
        parts = []
        if ros_setup and os.path.exists(ros_setup):
            parts.append("source '%s'" % ros_setup)
        ws_path = ws_setup or ""
        if not (ws_path and os.path.exists(os.path.expanduser(ws_path))):
            # 自动探测常见工作空间(兼容未手动配置的情况)
            ws_path = self._auto_detect_ws()
        if ws_path and os.path.exists(os.path.expanduser(ws_path)):
            parts.append("source '%s'" % os.path.expanduser(ws_path))
        if self.kind == "launch":
            parts.append("roslaunch '%s'" % self.path)
        else:
            parts.append("'%s' '%s'" % (self._py_interpreter(), self.path))
        if self.args.strip():
            parts[-1] += " " + self.args.strip()
        parts.append('echo "[进程已退出] 退出码: $?"')
        return " && ".join(parts)

    @staticmethod
    def _auto_detect_ws():
        """自动探测常见ROS工作空间"""
        import glob
        candidates = []
        home = os.path.expanduser("~")
        for ws in ("catkin_ws", "ros_ws", "ros_workspace", "dev_ws", "workspace"):
            candidates.append(os.path.join(home, ws, "devel", "setup.bash"))
        candidates.append("/opt/ros/noetic/setup.bash")
        for c in candidates:
            if os.path.exists(c):
                return c
        return ""

    def start(self, ros_setup, ws_setup, log_callback, finish_callback):
        if self.is_running():
            return
        cmd = self.build_command(ros_setup, ws_setup)
        if self.process is not None:
            self.process.deleteLater()  # 释放旧的 QProcess,避免泄漏
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(
            lambda: log_callback(self, self.process.readAllStandardOutput().data().decode(errors="replace"))
        )
        self.process.finished.connect(lambda code, status: finish_callback(self))
        # 用 setsid 让任务成为独立进程组的组长(pgid == pid),
        # 停止时 killpg 可以杀掉 roslaunch/gazebo 等所有子孙进程
        if platform.system() == "Windows":
            self.process.start("cmd", ["/c", cmd])
        else:
            self.process.start("setsid", ["bash", "-c", cmd])

    def stop(self):
        self.stop_requested = True
        if not (self.process and self.is_running()):
            return
        pid = self.process.processId()

        if platform.system() == "Windows":
            self.process.terminate()
            if not self.process.waitForFinished(2500):
                self.process.kill()
            return

        # 进程组的 pgid 等于组长进程 pid;killpg 给全组(含所有子孙进程)发信号
        killed = False
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
                killed = True
            except OSError:
                pass
        if not killed:
            self.process.terminate()
        if not self.process.waitForFinished(2500):
            if pid:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
            self.process.kill()

    def is_running(self):
        return self.process is not None and self.process.state() == QProcess.Running

    def exists(self, cache=None):
        if cache is not None and self.path in cache:
            return cache[self.path]
        result = os.path.isfile(self.path)
        if cache is not None:
            cache[self.path] = result
        return result

    def to_dict(self):
        return {
            "path": self.path,
            "args": self.args,
            "auto_restart": self.auto_restart,
            "auto_start": self.auto_start,
        }


