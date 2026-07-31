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

def test_config_import_nonexistent_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        import_path = os.path.join(tmpdir, "nonexistent.json")
        
        cm = ConfigManager(config_path)
        assert cm.import_config(import_path) is False

def test_config_export_import_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        export_path = os.path.join(tmpdir, "export.json")
        
        cm = ConfigManager(config_path)
        original = {"ros_setup": "/test/path", "ws_setup": "/ws/path", "start_delay": 5}
        cm.save(original)
        
        assert cm.export_config(export_path)
        
        new_cm = ConfigManager(os.path.join(tmpdir, "new_config.json"))
        assert new_cm.import_config(export_path)
        
        config = new_cm.load()
        assert config["ros_setup"] == "/test/path"
        assert config["ws_setup"] == "/ws/path"
        assert config["start_delay"] == 5