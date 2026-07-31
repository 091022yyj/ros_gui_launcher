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