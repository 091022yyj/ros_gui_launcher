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