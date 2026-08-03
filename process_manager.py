import os
import signal
from PyQt6.QtCore import QProcess, QTimer

class ProcessRow:
    def __init__(self, path, kind, args="", auto_restart=False, auto_start=False):
        self.path = path
        self.kind = kind
        self.args = args
        self.auto_restart = auto_restart
        self.auto_start = auto_start
        self.process = None
        self.stop_requested = False
        self.restart_count = 0

    def is_running(self):
        return self.process is not None and self.process.state() == QProcess.Running

    def exists(self):
        return os.path.isfile(self.path)

    def to_dict(self):
        return {
            "path": self.path,
            "args": self.args,
            "auto_restart": self.auto_restart,
            "auto_start": self.auto_start,
        }

class ProcessManager:
    def __init__(self):
        self.processes = []

    def add_process(self, process_row):
        self.processes.append(process_row)

    def remove_process(self, process_row):
        if process_row in self.processes:
            self.processes.remove(process_row)

    def start_process(self, process_row, ros_setup, ws_setup):
        if process_row.is_running():
            return False

        cmd = self._build_command(process_row, ros_setup, ws_setup)
        process_row.process = QProcess()
        process_row.process.setProcessChannelMode(QProcess.MergedChannels)
        process_row.process.start("setsid", ["bash", "-c", cmd])

        return process_row.is_running()

    def stop_process(self, process_row):
        if not process_row.is_running():
            return

        process_row.stop_requested = True
        pid = process_row.process.processId()

        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                pass

        if not process_row.process.waitForFinished(2500):
            if pid:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
            process_row.process.kill()

    def stop_all(self):
        for process in self.processes:
            self.stop_process(process)

    def _build_command(self, process_row, ros_setup, ws_setup):
        parts = []
        if ros_setup and os.path.exists(ros_setup):
            parts.append(f"source '{ros_setup}'")
        if ws_setup and os.path.exists(os.path.expanduser(ws_setup)):
            parts.append(f"source '{os.path.expanduser(ws_setup)}'")

        if process_row.kind == "launch":
            parts.append(f"roslaunch '{process_row.path}'")
        else:
            interpreter = self._get_interpreter(process_row.path)
            parts.append(f"'{interpreter}' '{process_row.path}'")

        if process_row.args.strip():
            parts[-1] += f" {process_row.args.strip()}"

        parts.append('echo "[进程已退出] 退出码: $?"')
        return " && ".join(parts)

    def _get_interpreter(self, path):
        try:
            with open(path, 'rb') as f:
                first = f.readline().decode('utf-8', errors='replace').strip()
            if first.startswith('#!'):
                parts = first[2:].strip().split()
                if parts and parts[0].endswith('env') and len(parts) > 1:
                    return parts[1]
                if parts:
                    return parts[0]
        except:
            pass
        return 'python3'
