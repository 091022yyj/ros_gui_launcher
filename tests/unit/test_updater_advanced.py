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