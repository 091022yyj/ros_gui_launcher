import psutil
import time
from datetime import datetime

class ProcessMonitor:
    def __init__(self):
        self.processes = {}
        self.history = {}

    def add_process(self, process_name):
        self.processes[process_name] = {
            "status": "stopped",
            "start_time": None,
            "cpu_usage": 0,
            "memory_usage": 0,
            "threads": 0,
        }
        self.history[process_name] = []

    def remove_process(self, process_name):
        if process_name in self.processes:
            del self.processes[process_name]
        if process_name in self.history:
            del self.history[process_name]

    def update_process_status(self, process_name, status, pid=None):
        if process_name not in self.processes:
            self.add_process(process_name)

        self.processes[process_name]["status"] = status
        if status == "running" and pid:
            self.processes[process_name]["start_time"] = datetime.now()

        self.history[process_name].append({
            "time": datetime.now(),
            "status": status,
        })

    def get_process_info(self, process_name):
        return self.processes.get(process_name, {})

    def get_process_history(self, process_name):
        return self.history.get(process_name, [])

    def get_system_resources(self):
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
        }
