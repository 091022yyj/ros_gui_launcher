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
        """清理命令，防止注入"""
        # 危险字符列表
        dangerous_chars = [";", "|", "&", "$", "`", ">", "<", "(", ")"]
        # 危险命令列表
        dangerous_commands = ["rm", "mv", "cp", "chmod", "chown", "kill", "pkill"]
        
        parts = command.split()
        cleaned_parts = []
        
        for part in parts:
            # 检查是否包含危险字符
            if any(char in part for char in dangerous_chars):
                continue
            # 检查是否是危险命令
            if part in dangerous_commands:
                continue
            cleaned_parts.append(part)
        
        return " ".join(cleaned_parts)
    
    def check_file_permissions(self, path):
        """检查文件权限"""
        if not os.path.exists(path):
            return False
        return os.access(path, os.X_OK)