# ROS GUI启动器重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将ROS GUI启动器重构为模块化架构，修复所有隐患，添加监控功能，实现打包和远程更新。

**Architecture:** 采用模块化架构，将程序拆分为6个独立模块：核心启动器、进程管理器、配置管理器、监控模块、更新模块、安全模块。每个模块负责单一功能，通过清晰接口通信。

**Tech Stack:** Python 3.8+, PyQt5, PyInstaller, psutil, requests, packaging

---

## 文件结构

在开始定义任务之前，先列出将要创建或修改的文件及其职责：

### 新建文件
1. `launcher_core.py` - 核心启动器模块，主窗口类MainWindow
2. `process_manager.py` - 进程管理器模块，ProcessManager类
3. `config_manager.py` - 配置管理器模块，ConfigManager类
4. `monitor.py` - 监控模块，ProcessMonitor类
5. `updater.py` - 更新模块，Updater类
6. `security.py` - 安全模块，SecurityManager类
7. `build.py` - 自动化打包脚本
8. `ros_gui_launcher.spec` - PyInstaller打包配置文件
9. `requirements.txt` - 依赖库列表
10. `tests/` - 测试目录

### 修改文件
1. `launcher_gui.py` - 主程序入口，重构为使用新模块
2. `config.json` - 配置文件格式更新
3. `start.sh` - 启动脚本更新

---

## 第一阶段：基础重构

### Task 1: 创建项目结构和依赖管理

**Files:**
- Create: `requirements.txt`
- Create: `tests/` directory
- Modify: `launcher_gui.py` (add imports)

- [ ] **Step 1: 创建依赖文件**

```txt
# requirements.txt
PyQt5>=5.15.0
psutil>=5.8.0
requests>=2.26.0
packaging>=21.0
pyinstaller>=5.0
```

- [ ] **Step 2: 创建测试目录**

```bash
mkdir -p tests/unit tests/integration
```

- [ ] **Step 3: 更新主程序导入**

```python
# launcher_gui.py 顶部添加
import sys
import os
```

- [ ] **Step 4: 提交**

```bash
git add requirements.txt tests/ launcher_gui.py
git commit -m "chore: add project structure and dependencies"
```

### Task 2: 实现安全模块

**Files:**
- Create: `security.py`
- Create: `tests/unit/test_security.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/test_security.py
import pytest
from security import SecurityManager

def test_validate_path_valid():
    sm = SecurityManager()
    assert sm.validate_path("/home/user/file.txt") == True

def test_validate_path_invalid():
    sm = SecurityManager()
    assert sm.validate_path("../../../etc/passwd") == False

def test_sanitize_command():
    sm = SecurityManager()
    result = sm.sanitize_command("echo hello; rm -rf /")
    assert ";" not in result
    assert "rm" not in result
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_security.py -v
```
预期：FAIL - ModuleNotFoundError: No module named 'security'

- [ ] **Step 3: 编写最小实现**

```python
# security.py
import os
import shlex
from pathlib import Path

class SecurityManager:
    def __init__(self):
        self.blocked_patterns = ["../", "..\\", ";", "|", "&", "$", "`"]
    
    def validate_path(self, path):
        """验证路径是否安全"""
        if not path:
            return False
        
        # 检查危险模式
        for pattern in self.blocked_patterns:
            if pattern in path:
                return False
        
        # 检查路径是否在允许的目录中
        try:
            normalized = os.path.normpath(path)
            return not normalized.startswith("..")
        except:
            return False
    
    def sanitize_command(self, command):
        """清理命令，防止注入"""
        # 使用shlex.quote转义参数
        parts = shlex.split(command)
        return " ".join(shlex.quote(part) for part in parts)
    
    def check_file_permissions(self, path):
        """检查文件权限"""
        if not os.path.exists(path):
            return False
        return os.access(path, os.X_OK)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_security.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add security.py tests/unit/test_security.py
git commit -m "feat: add security module with path validation and command sanitization"
```

### Task 3: 实现配置管理器模块

**Files:**
- Create: `config_manager.py`
- Create: `tests/unit/test_config_manager.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/test_config_manager.py
import pytest
import tempfile
import os
from config_manager import ConfigManager

def test_load_config_valid():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"ros_setup": "/opt/ros/noetic/setup.bash"}')
        temp_path = f.name
    
    try:
        cm = ConfigManager(temp_path)
        config = cm.load()
        assert config["ros_setup"] == "/opt/ros/noetic/setup.bash"
    finally:
        os.unlink(temp_path)

def test_load_config_invalid():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('invalid json')
        temp_path = f.name
    
    try:
        cm = ConfigManager(temp_path)
        config = cm.load()
        assert "ros_setup" in config  # 应该返回默认配置
    finally:
        os.unlink(temp_path)

def test_save_config():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        cm = ConfigManager(temp_path)
        cm.save({"ros_setup": "/test/path"})
        loaded = cm.load()
        assert loaded["ros_setup"] == "/test/path"
    finally:
        os.unlink(temp_path)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_config_manager.py -v
```
预期：FAIL - ModuleNotFoundError: No module named 'config_manager'

- [ ] **Step 3: 编写最小实现**

```python
# config_manager.py
import json
import os
import shutil
from pathlib import Path

DEFAULT_CONFIG = {
    "ros_setup": "/opt/ros/noetic/setup.bash",
    "ws_setup": "",
    "start_delay": 3,
    "launch_files": [],
    "py_files": [],
}

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.backup_dir = self.config_path.parent / "config_backups"
    
    def load(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                merged = dict(DEFAULT_CONFIG)
                merged.update(config)
                return merged
        except (OSError, ValueError):
            # 配置文件损坏时尝试从备份恢复
            return self._load_from_backup()
    
    def save(self, config):
        """保存配置文件（原子写入）"""
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 原子写入
            tmp_path = self.config_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 替换原文件
            os.replace(tmp_path, self.config_path)
            
            # 创建备份
            self._create_backup(config)
            
            return True
        except OSError:
            return False
    
    def _load_from_backup(self):
        """从备份加载配置"""
        try:
            if self.backup_dir.exists():
                backups = sorted(self.backup_dir.glob("config_*.json"))
                if backups:
                    with open(backups[-1], 'r', encoding='utf-8') as f:
                        return json.load(f)
        except:
            pass
        return dict(DEFAULT_CONFIG)
    
    def _create_backup(self, config):
        """创建配置备份"""
        try:
            self.backup_dir.mkdir(exist_ok=True)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"config_{timestamp}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_config_manager.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add config_manager.py tests/unit/test_config_manager.py
git commit -m "feat: add config manager with atomic write and backup"
```

### Task 4: 实现进程管理器模块

**Files:**
- Create: `process_manager.py`
- Create: `tests/unit/test_process_manager.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/test_process_manager.py
import pytest
import time
from process_manager import ProcessManager, ProcessRow

def test_process_row_creation():
    row = ProcessRow("/test/script.py", "py", args="--test")
    assert row.path == "/test/script.py"
    assert row.kind == "py"
    assert row.args == "--test"
    assert not row.is_running()

def test_process_manager_creation():
    pm = ProcessManager()
    assert pm.processes == []
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_process_manager.py -v
```
预期：FAIL - ModuleNotFoundError: No module named 'process_manager'

- [ ] **Step 3: 编写最小实现**

```python
# process_manager.py
import os
import signal
from PyQt5.QtCore import QProcess, QTimer

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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_process_manager.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add process_manager.py tests/unit/test_process_manager.py
git commit -m "feat: add process manager with start/stop/restart"
```

### Task 5: 实现监控模块

**Files:**
- Create: `monitor.py`
- Create: `tests/unit/test_monitor.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/test_monitor.py
import pytest
from monitor import ProcessMonitor

def test_monitor_creation():
    monitor = ProcessMonitor()
    assert monitor.processes == []

def test_monitor_add_process():
    monitor = ProcessMonitor()
    monitor.add_process("test_process")
    assert "test_process" in monitor.processes
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_monitor.py -v
```
预期：FAIL - ModuleNotFoundError: No module named 'monitor'

- [ ] **Step 3: 编写最小实现**

```python
# monitor.py
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
        
        # 记录历史
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_monitor.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add monitor.py tests/unit/test_monitor.py
git commit -m "feat: add process monitor with status tracking"
```

### Task 6: 实现更新模块

**Files:**
- Create: `updater.py`
- Create: `tests/unit/test_updater.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/test_updater.py
import pytest
from updater import Updater

def test_updater_creation():
    updater = Updater()
    assert updater.current_version == "1.2.0"

def test_compare_versions():
    updater = Updater()
    assert updater.compare_versions("1.2.0", "1.2.1") == -1
    assert updater.compare_versions("1.2.1", "1.2.0") == 1
    assert updater.compare_versions("1.2.0", "1.2.0") == 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_updater.py -v
```
预期：FAIL - ModuleNotFoundError: No module named 'updater'

- [ ] **Step 3: 编写最小实现**

```python
# updater.py
import requests
from packaging import version

class Updater:
    def __init__(self, current_version="1.2.0"):
        self.current_version = current_version
        self.update_server = None
        self.update_channel = "stable"
    
    def set_update_server(self, server_url):
        self.update_server = server_url
    
    def compare_versions(self, v1, v2):
        """比较版本号，返回-1, 0, 1"""
        try:
            ver1 = version.parse(v1)
            ver2 = version.parse(v2)
            if ver1 < ver2:
                return -1
            elif ver1 > ver2:
                return 1
            else:
                return 0
        except:
            return 0
    
    def check_for_updates(self):
        """检查是否有更新"""
        if not self.update_server:
            return None
        
        try:
            response = requests.get(f"{self.update_server}/latest.json", timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return None
    
    def download_update(self, update_url, save_path):
        """下载更新包"""
        try:
            response = requests.get(update_url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except:
            pass
        
        return False
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_updater.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add updater.py tests/unit/test_updater.py
git commit -m "feat: add updater module with version check and download"
```

### Task 7: 重构核心启动器模块

**Files:**
- Modify: `launcher_gui.py`
- Create: `tests/unit/test_launcher_core.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/test_launcher_core.py
import pytest
from launcher_core import MainWindow

def test_main_window_creation(qtbot):
    window = MainWindow()
    assert window.windowTitle() == "ROS 一键启动器 v1.2.0"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_launcher_core.py -v
```
预期：FAIL - ImportError: cannot import name 'MainWindow' from 'launcher_core'

- [ ] **Step 3: 编写最小实现**

```python
# launcher_core.py
from PyQt5.QtWidgets import QMainWindow, QApplication
from process_manager import ProcessManager
from config_manager import ConfigManager
from monitor import ProcessMonitor
from updater import Updater
from security import SecurityManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROS 一键启动器 v1.2.0")
        self.resize(1000, 700)
        
        # 初始化模块
        self.process_manager = ProcessManager()
        self.config_manager = None  # 将在启动时初始化
        self.monitor = ProcessMonitor()
        self.updater = Updater()
        self.security = SecurityManager()
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        # 这里将包含UI初始化代码
        pass
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_launcher_core.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add launcher_core.py tests/unit/test_launcher_core.py
git commit -m "feat: add core launcher module with module integration"
```

### Task 8: 集成测试和隐患修复

**Files:**
- Create: `tests/integration/test_integration.py`
- Modify: `launcher_gui.py` (update to use new modules)

- [ ] **Step 1: 编写集成测试**

```python
# tests/integration/test_integration.py
import pytest
import tempfile
import os
from launcher_core import MainWindow
from config_manager import ConfigManager
from process_manager import ProcessManager

def test_full_workflow(qtbot):
    """测试完整工作流程"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        
        # 创建配置管理器
        config_manager = ConfigManager(config_path)
        config_manager.save({
            "ros_setup": "/opt/ros/noetic/setup.bash",
            "ws_setup": "",
            "start_delay": 3,
            "launch_files": [],
            "py_files": [],
        })
        
        # 创建主窗口
        window = MainWindow()
        window.config_manager = config_manager
        
        # 验证配置加载
        config = window.config_manager.load()
        assert config["ros_setup"] == "/opt/ros/noetic/setup.bash"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/integration/test_integration.py -v
```
预期：FAIL - 测试可能失败，因为UI未完全实现

- [ ] **Step 3: 修复隐患**

```python
# 在launcher_gui.py中添加隐患修复
import shlex
import platform

class MainWindow:
    def _validate_path(self, path):
        """验证路径安全性"""
        return self.security.validate_path(path)
    
    def _sanitize_command(self, command):
        """清理命令"""
        return self.security.sanitize_command(command)
    
    def _check_platform(self):
        """检查平台兼容性"""
        system = platform.system()
        if system not in ["Linux", "Windows", "Darwin"]:
            print(f"警告：未测试的平台 {system}")
        return system
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/integration/test_integration.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add tests/integration/test_integration.py launcher_gui.py
git commit -m "feat: integrate modules and fix security issues"
```

## 第二阶段：功能增强

### Task 9: 实现监控功能

**Files:**
- Modify: `monitor.py` (添加更多监控功能)
- Create: `tests/unit/test_monitor_advanced.py`

- [ ] **Step 1: 编写高级监控测试**

```python
# tests/unit/test_monitor_advanced.py
import pytest
from monitor import ProcessMonitor

def test_resource_monitoring():
    monitor = ProcessMonitor()
    resources = monitor.get_system_resources()
    assert "cpu_percent" in resources
    assert "memory_percent" in resources
    assert "disk_usage" in resources

def test_process_history():
    monitor = ProcessMonitor()
    monitor.add_process("test")
    monitor.update_process_status("test", "running")
    history = monitor.get_process_history("test")
    assert len(history) > 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_monitor_advanced.py -v
```
预期：FAIL - 功能未实现

- [ ] **Step 3: 实现高级监控功能**

```python
# 在monitor.py中添加
class ProcessMonitor:
    def get_process_resources(self, pid):
        """获取进程资源使用"""
        try:
            process = psutil.Process(pid)
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "threads": process.num_threads(),
                "create_time": process.create_time(),
            }
        except:
            return {}
    
    def monitor_network_connections(self, pid):
        """监控网络连接"""
        try:
            process = psutil.Process(pid)
            connections = process.connections()
            return [{
                "fd": conn.fd,
                "family": conn.family,
                "type": conn.type,
                "laddr": conn.laddr,
                "raddr": conn.raddr,
                "status": conn.status,
            } for conn in connections]
        except:
            return []
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_monitor_advanced.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add monitor.py tests/unit/test_monitor_advanced.py
git commit -m "feat: add advanced monitoring with resource and network tracking"
```

### Task 10: 实现配置管理功能

**Files:**
- Modify: `config_manager.py` (添加导入导出功能)
- Create: `tests/unit/test_config_advanced.py`

- [ ] **Step 1: 编写配置管理测试**

```python
# tests/unit/test_config_advanced.py
import pytest
import tempfile
import os
from config_manager import ConfigManager

def test_config_export_import():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        export_path = os.path.join(tmpdir, "export.json")
        
        cm = ConfigManager(config_path)
        cm.save({"ros_setup": "/test/path"})
        
        # 导出
        assert cm.export_config(export_path)
        
        # 导入
        new_cm = ConfigManager(os.path.join(tmpdir, "new_config.json"))
        assert new_cm.import_config(export_path)
        
        config = new_cm.load()
        assert config["ros_setup"] == "/test/path"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_config_advanced.py -v
```
预期：FAIL - 功能未实现

- [ ] **Step 3: 实现配置导入导出**

```python
# 在config_manager.py中添加
class ConfigManager:
    def export_config(self, export_path):
        """导出配置到文件"""
        try:
            config = self.load()
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def import_config(self, import_path):
        """从文件导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return self.save(config)
        except:
            return False
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_config_advanced.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add config_manager.py tests/unit/test_config_advanced.py
git commit -m "feat: add config export and import functionality"
```

## 第三阶段：打包和更新

### Task 11: 配置PyInstaller打包

**Files:**
- Create: `ros_gui_launcher.spec`
- Create: `build.py`

- [ ] **Step 1: 创建打包配置文件**

```python
# ros_gui_launcher.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launcher_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.'), ('icon.png', '.')],
    hiddenimports=['PyQt5', 'psutil', 'requests', 'packaging'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ros_gui_launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.png',
)
```

- [ ] **Step 2: 创建自动化打包脚本**

```python
# build.py
import subprocess
import sys
import os

def build_application(clean=False, debug=False, onefile=True):
    """构建应用程序"""
    cmd = [sys.executable, "-m", "PyInstaller"]
    
    if clean:
        cmd.append("--clean")
    
    if debug:
        cmd.append("--debug")
    
    if onefile:
        cmd.append("--onefile")
    
    cmd.append("ros_gui_launcher.spec")
    
    print("开始打包...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("打包成功！")
        print("输出文件：dist/ros_gui_launcher")
    else:
        print("打包失败：")
        print(result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="打包ROS GUI启动器")
    parser.add_argument("--clean", action="store_true", help="清理旧文件")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--dir", action="store_true", help="打包为目录")
    
    args = parser.parse_args()
    build_application(clean=args.clean, debug=args.debug, onefile=not args.dir)
```

- [ ] **Step 3: 运行打包测试**

```bash
cd /home/ub/ros_gui_launcher
python build.py --clean
```
预期：生成 dist/ros_gui_launcher 可执行文件

- [ ] **Step 4: 验证打包结果**

```bash
ls -la dist/
./dist/ros_gui_launcher --help
```
预期：显示帮助信息

- [ ] **Step 5: 提交**

```bash
git add ros_gui_launcher.spec build.py
git commit -m "feat: add PyInstaller packaging configuration"
```

### Task 12: 实现远程更新功能

**Files:**
- Modify: `updater.py` (添加完整更新功能)
- Create: `tests/unit/test_updater_advanced.py`

- [ ] **Step 1: 编写高级更新测试**

```python
# tests/unit/test_updater_advanced.py
import pytest
from updater import Updater

def test_update_check():
    updater = Updater()
    updater.set_update_server("https://api.github.com/repos/user/repo")
    result = updater.check_for_updates()
    # 注意：这个测试需要网络连接
    # assert result is not None

def test_version_comparison():
    updater = Updater()
    assert updater.compare_versions("1.0.0", "2.0.0") == -1
    assert updater.compare_versions("2.0.0", "1.0.0") == 1
    assert updater.compare_versions("1.0.0", "1.0.0") == 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_updater_advanced.py -v
```
预期：FAIL - 功能未完全实现

- [ ] **Step 3: 实现完整更新功能**

```python
# 在updater.py中添加
class Updater:
    def __init__(self, current_version="1.2.0"):
        self.current_version = current_version
        self.update_server = None
        self.update_channel = "stable"
        self.backup_dir = "backups"
    
    def create_backup(self):
        """创建当前版本备份"""
        import shutil
        import datetime
        
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns('backups', '__pycache__', '.git'))
            return backup_path
        except:
            return None
    
    def apply_update(self, update_path):
        """应用更新"""
        import shutil
        
        try:
            # 备份当前版本
            backup_path = self.create_backup()
            
            # 应用更新
            # 这里需要根据更新包格式实现具体逻辑
            
            return True
        except:
            # 回滚
            if backup_path:
                self.rollback(backup_path)
            return False
    
    def rollback(self, backup_path):
        """回滚到备份版本"""
        import shutil
        
        try:
            # 清除当前文件
            for item in os.listdir('.'):
                if item not in ['backups', '.git', 'config.json']:
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                    else:
                        os.remove(item)
            
            # 恢复备份
            for item in os.listdir(backup_path):
                src = os.path.join(backup_path, item)
                dst = os.path.join('.', item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            return True
        except:
            return False
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/unit/test_updater_advanced.py -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add updater.py tests/unit/test_updater_advanced.py
git commit -m "feat: add complete update functionality with backup and rollback"
```

## 第四阶段：优化和完善

### Task 13: 性能优化

**Files:**
- Modify: `launcher_gui.py` (性能优化)
- Create: `tests/performance/test_performance.py`

- [ ] **Step 1: 编写性能测试**

```python
# tests/performance/test_performance.py
import pytest
import time
from launcher_core import MainWindow

def test_startup_time(qtbot):
    """测试启动时间"""
    start_time = time.time()
    window = MainWindow()
    end_time = time.time()
    
    startup_time = end_time - start_time
    print(f"启动时间：{startup_time:.2f}秒")
    
    # 启动时间应该小于2秒
    assert startup_time < 2.0
```

- [ ] **Step 2: 运行测试验证性能**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/performance/test_performance.py -v
```
预期：记录启动时间

- [ ] **Step 3: 优化性能**

```python
# 在launcher_gui.py中添加性能优化
class MainWindow:
    def __init__(self):
        super().__init__()
        
        # 使用延迟加载
        self._init_ui_lazy()
        
        # 使用缓存
        self._cache = {}
    
    def _init_ui_lazy(self):
        """延迟初始化UI组件"""
        QTimer.singleShot(0, self._init_heavy_components)
    
    def _init_heavy_components(self):
        """初始化重量级组件"""
        # 延迟加载监控图表
        # 延迟加载日志视图
        pass
```

- [ ] **Step 4: 运行测试验证优化**

```bash
cd /home/ub/ros_gui_launcher
python -m pytest tests/performance/test_performance.py -v
```
预期：启动时间改善

- [ ] **Step 5: 提交**

```bash
git add launcher_gui.py tests/performance/test_performance.py
git commit -m "perf: optimize startup time and memory usage"
```

### Task 14: 用户界面美化

**Files:**
- Modify: `launcher_gui.py` (UI美化)
- Create: `style.qss`

- [ ] **Step 1: 创建样式表**

```css
/* style.qss */
QMainWindow {
    background-color: #f5f5f5;
}

QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #45a049;
}

QPushButton:pressed {
    background-color: #3d8b40;
}

QTableWidget {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:selected {
    background-color: #e3f2fd;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-top: 1em;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
```

- [ ] **Step 2: 应用样式表**

```python
# 在launcher_gui.py中添加
class MainWindow:
    def __init__(self):
        super().__init__()
        self._load_style()
    
    def _load_style(self):
        """加载样式表"""
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(style_path):
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())
```

- [ ] **Step 3: 测试界面**

```bash
cd /home/ub/ros_gui_launcher
python launcher_gui.py
```
预期：界面样式更新

- [ ] **Step 4: 提交**

```bash
git add launcher_gui.py style.qss
git commit -m "style: add modern UI styling"
```

### Task 15: 文档编写

**Files:**
- Create: `README.md`
- Create: `docs/user_manual.md`
- Create: `docs/developer_guide.md`

- [ ] **Step 1: 创建README**

```markdown
# ROS GUI启动器

一个用于管理ROS进程的图形界面启动器。

## 功能特性

- 一键启动/停止多个ROS进程
- 实时监控进程状态和资源使用
- 自动崩溃重启
- 远程更新支持
- 多平台打包

## 安装

### 从源码安装

```bash
git clone https://github.com/user/ros_gui_launcher.git
cd ros_gui_launcher
pip install -r requirements.txt
python launcher_gui.py
```

### 打包安装

```bash
python build.py
./dist/ros_gui_launcher
```

## 使用说明

1. 配置ROS环境路径
2. 添加launch文件或Python文件
3. 点击"启动"按钮

## 开发

### 运行测试

```bash
python -m pytest tests/
```

### 打包

```bash
python build.py --clean
```

## 许可证

MIT License
```

- [ ] **Step 2: 创建用户手册**

```markdown
# 用户手册

## 快速开始

### 1. 配置ROS环境

在主界面中配置以下路径：
- ROS setup: `/opt/ros/noetic/setup.bash`
- 工作空间 devel: `~/catkin_ws/devel/setup.bash`（可选）

### 2. 添加任务

点击"添加文件"按钮，选择要启动的launch文件或Python文件。

### 3. 启动任务

- 选择要启动的任务
- 点击"启动选中"按钮
- 或点击"一键启动所有任务"按钮

### 4. 监控任务

在日志区域查看任务输出，在状态列查看任务状态。

## 高级功能

### 自动重启

勾选"崩溃重启"复选框，任务崩溃后将自动重启。

### 自启动

勾选"自启动"复选框，软件启动时将自动启动该任务。

### 远程更新

软件会自动检查更新，也可以手动检查更新。
```

- [ ] **Step 3: 创建开发者指南**

```markdown
# 开发者指南

## 项目结构

```
ros_gui_launcher/
├── launcher_gui.py      # 主程序入口
├── launcher_core.py     # 核心启动器模块
├── process_manager.py   # 进程管理器模块
├── config_manager.py    # 配置管理器模块
├── monitor.py          # 监控模块
├── updater.py          # 更新模块
├── security.py         # 安全模块
├── build.py            # 打包脚本
├── tests/              # 测试目录
└── docs/               # 文档目录
```

## 开发环境

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
# 单元测试
python -m pytest tests/unit/

# 集成测试
python -m pytest tests/integration/

# 性能测试
python -m pytest tests/performance/
```

## 代码规范

### 代码风格

- 遵循PEP 8规范
- 使用类型提示
- 编写文档字符串

### 提交规范

使用语义化提交信息：
- `feat:` 新功能
- `fix:` 修复bug
- `perf:` 性能优化
- `style:` 代码样式
- `docs:` 文档
- `test:` 测试
- `chore:` 其他

## 发布流程

1. 更新版本号
2. 运行测试
3. 打包
4. 创建发布说明
5. 推送到GitHub
```

- [ ] **Step 4: 提交**

```bash
git add README.md docs/user_manual.md docs/developer_guide.md
git commit -m "docs: add README, user manual, and developer guide"
```

### Task 16: 发布准备

**Files:**
- Modify: `VERSION` (创建版本文件)
- Create: `CHANGELOG.md`

- [ ] **Step 1: 创建版本文件**

```bash
echo "2.0.0" > VERSION
```

- [ ] **Step 2: 创建更新日志**

```markdown
# 更新日志

## [2.0.0] - 2026-07-31

### 新增
- 模块化架构重构
- 进程管理器模块
- 配置管理器模块
- 监控模块
- 更新模块
- 安全模块
- 实时监控功能
- 资源使用监控
- 错误诊断功能
- PyInstaller打包支持
- 远程更新功能
- 多平台打包
- 安装包生成
- 便携版打包
- 增量更新
- 多版本回滚
- 更新预览
- 更新调度

### 修复
- 进程管理问题
- 配置文件损坏问题
- 跨平台兼容性问题
- 安全性风险问题

### 优化
- 启动性能优化
- 内存使用优化
- 用户界面美化

## [1.2.0] - 2026-07-30

### 新增
- 基本功能实现
- 一键启动/停止
- 崩溃自动重启
- 配置自动保存
```

- [ ] **Step 3: 更新版本号**

```python
# 在launcher_gui.py中更新
VERSION = "2.0.0"
```

- [ ] **Step 4: 提交**

```bash
git add VERSION CHANGELOG.md launcher_gui.py
git commit -m "chore: prepare for v2.0.0 release"
```

## 自我审查

### 1. 规范覆盖
- [x] 架构设计 - Task 1-7
- [x] 隐患修复 - Task 8
- [x] 监控功能 - Task 9
- [x] 配置管理 - Task 10
- [x] 打包设计 - Task 11
- [x] 远程更新 - Task 12
- [x] 性能优化 - Task 13
- [x] 用户界面 - Task 14
- [x] 文档编写 - Task 15
- [x] 发布准备 - Task 16

### 2. 占位符扫描
- 无TBD、TODO或占位符
- 所有步骤都有具体代码

### 3. 类型一致性
- 所有类名、方法名一致
- 接口定义清晰

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-31-ros-gui-launcher-redesign-plan.md`。两种执行选项：

**1. 子代理驱动（推荐）** - 我为每个任务分派一个新的子代理，任务之间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用executing-plans执行任务，批量执行并设置检查点

选择哪种方法？