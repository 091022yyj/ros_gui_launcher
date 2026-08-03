import os
import shlex
from pathlib import Path

class SecurityManager:
    def __init__(self):
        self.blocked_patterns = ["../", "..\\", ";", "|", "&", "$", "`"]
    
    def validate_path(self, path):
        """验证路径是否安全"""
        if not path:
            return False
        
        # 检查危险模式
        for pattern in self.blocked_patterns:
            if pattern in path:
                return False
        
        # 检查路径是否在允许的目录中
        try:
            normalized = os.path.normpath(path)
            return not normalized.startswith("..")
        except:
            return False
    
    def sanitize_command(self, command):
        """清理命令，防止注入。发现危险字符则返回空字符串（拒绝执行）"""
        dangerous_chars = [";", "|", "&", "$", "`", ">", "<", "(", ")"]
        for char in dangerous_chars:
            if char in command:
                return ""  # 拒绝执行，而不是截断
        return command.strip()
    
    def check_file_permissions(self, path):
        """检查文件权限(读权限即可,launch/py文件无需可执行权限)"""
        if not os.path.exists(path):
            return False
        return os.access(path, os.R_OK)