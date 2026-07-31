# tests/unit/test_security.py
import pytest
from security import SecurityManager

def test_validate_path_valid():
    sm = SecurityManager()
    assert sm.validate_path("/home/user/file.txt") == True

def test_validate_path_invalid():
    sm = SecurityManager()
    assert sm.validate_path("../../../etc/passwd") == False

def test_sanitize_command():
    sm = SecurityManager()
    result = sm.sanitize_command("echo hello; rm -rf /")
    assert ";" not in result
    assert "rm" not in result