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

def test_process_manager_add_process():
    pm = ProcessManager()
    row = ProcessRow("/test/script.py", "py")
    pm.add_process(row)
    assert len(pm.processes) == 1
    assert pm.processes[0] == row

def test_process_manager_remove_process():
    pm = ProcessManager()
    row = ProcessRow("/test/script.py", "py")
    pm.add_process(row)
    pm.remove_process(row)
    assert len(pm.processes) == 0

def test_process_row_exists():
    row = ProcessRow("/bin/ls", "sh")
    assert row.exists()
    
    row2 = ProcessRow("/nonexistent/file.py", "py")
    assert not row2.exists()

def test_process_row_to_dict():
    row = ProcessRow("/test/script.py", "py", args="--test", auto_restart=True, auto_start=False)
    d = row.to_dict()
    assert d["path"] == "/test/script.py"
    assert d["args"] == "--test"
    assert d["auto_restart"] is True
    assert d["auto_start"] is False