import pytest
import psutil
from monitor import ProcessMonitor


def test_get_system_resources():
    monitor = ProcessMonitor()
    resources = monitor.get_system_resources()
    assert "cpu_percent" in resources
    assert "memory_percent" in resources
    assert "disk_usage" in resources
    assert isinstance(resources["cpu_percent"], (int, float))
    assert isinstance(resources["memory_percent"], (int, float))
    assert isinstance(resources["disk_usage"], (int, float))


def test_process_history():
    monitor = ProcessMonitor()
    monitor.add_process("test")
    monitor.update_process_status("test", "running")
    history = monitor.get_process_history("test")
    assert len(history) > 0
    assert history[0]["status"] == "running"


def test_get_process_resources():
    monitor = ProcessMonitor()
    current_pid = psutil.Process().pid
    resources = monitor.get_process_resources(current_pid)
    assert "cpu_percent" in resources
    assert "memory_percent" in resources
    assert "threads" in resources
    assert "create_time" in resources
    assert isinstance(resources["cpu_percent"], (int, float))
    assert isinstance(resources["memory_percent"], (int, float))
    assert isinstance(resources["threads"], int)
    assert isinstance(resources["create_time"], float)


def test_get_process_resources_invalid_pid():
    monitor = ProcessMonitor()
    resources = monitor.get_process_resources(999999999)
    assert resources == {}


def test_monitor_network_connections():
    monitor = ProcessMonitor()
    current_pid = psutil.Process().pid
    connections = monitor.monitor_network_connections(current_pid)
    assert isinstance(connections, list)
    if len(connections) > 0:
        conn = connections[0]
        assert "fd" in conn
        assert "family" in conn
        assert "type" in conn
        assert "laddr" in conn
        assert "raddr" in conn
        assert "status" in conn


def test_monitor_network_connections_invalid_pid():
    monitor = ProcessMonitor()
    connections = monitor.monitor_network_connections(999999999)
    assert connections == []