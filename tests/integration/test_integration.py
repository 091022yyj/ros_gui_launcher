import pytest
import tempfile
import os
from PyQt6.QtWidgets import QApplication
from launcher_core import MainWindow
from config_manager import ConfigManager
from process_manager import ProcessManager

app = QApplication([])

def test_full_workflow():
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

def test_config_roundtrip():
    """测试配置保存和加载的往返一致性"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        
        config_manager = ConfigManager(config_path)
        original = {
            "ros_setup": "/opt/ros/melodic/setup.bash",
            "ws_setup": "/home/user/catkin_ws/devel/setup.bash",
            "start_delay": 5,
            "launch_files": [{"path": "/path/to/file.launch", "args": "arg1:=val1", "auto_restart": True, "auto_start": False}],
            "py_files": [],
        }
        config_manager.save(original)
        loaded = config_manager.load()
        
        assert loaded["ros_setup"] == original["ros_setup"]
        assert loaded["ws_setup"] == original["ws_setup"]
        assert loaded["start_delay"] == original["start_delay"]
        assert loaded["launch_files"] == original["launch_files"]

def test_config_backup_created():
    """测试配置备份是否创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        
        config_manager = ConfigManager(config_path)
        config_manager.save({"ros_setup": "/opt/ros/noetic/setup.bash"})
        
        backup_dir = config_manager.backup_dir
        assert backup_dir.exists()
        backups = list(backup_dir.glob("config_*.json"))
        assert len(backups) >= 1

def test_main_window_has_modules():
    """测试主窗口是否正确初始化了各模块"""
    window = MainWindow()
    assert window.process_manager is not None
    assert window.monitor is not None
    assert window.updater is not None
    assert window.security is not None