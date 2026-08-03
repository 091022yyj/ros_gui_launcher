import pytest
from PyQt6.QtWidgets import QApplication
from launcher_core import MainWindow

def test_main_window_creation():
    app = QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "ROS 一键启动器 v1.2.0"