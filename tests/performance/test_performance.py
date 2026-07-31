import pytest
import time
import os
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope="module")
def app():
    return QApplication([])

def test_startup_time(app):
    """测试启动时间"""
    from launcher_gui import MainWindow
    start_time = time.time()
    window = MainWindow()
    end_time = time.time()
    window.close()
    
    startup_time = end_time - start_time
    print(f"启动时间：{startup_time:.2f}秒")
    
    assert startup_time < 2.0

def test_memory_usage(app):
    """测试内存使用"""
    from launcher_gui import MainWindow
    window = MainWindow()
    
    pid = os.getpid()
    
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    memory_kb = int(line.split()[1])
                    memory_mb = memory_kb / 1024
                    print(f"内存使用：{memory_mb:.2f} MB")
                    assert memory_mb < 200
                    break
    except (FileNotFoundError, IOError):
        pass
    finally:
        window.close()

def test_file_existence_cache(app):
    """测试文件存在性缓存"""
    from launcher_gui import MainWindow
    window = MainWindow()
    
    assert hasattr(window, '_file_exists_cache')
    assert isinstance(window._file_exists_cache, dict)
    window.close()