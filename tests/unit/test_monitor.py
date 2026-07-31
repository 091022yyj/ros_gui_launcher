import pytest
from monitor import ProcessMonitor

def test_monitor_creation():
    monitor = ProcessMonitor()
    assert monitor.processes == {}

def test_monitor_add_process():
    monitor = ProcessMonitor()
    monitor.add_process("test_process")
    assert "test_process" in monitor.processes