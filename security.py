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
        # 危险字符列表 - 找到第一个危险字符，截断命令
        dangerous_chars = [";", "|", "&", "$", "`", ">", "<", "(", ")"]
        
        # 找到第一个危险字符的位置
        min_pos = len(command)
        for char in dangerous_chars:
            pos = command.find(char)
            if pos != -1 and pos < min_pos:
                min_pos = pos
        
        # 截断到危险字符之前
        command = command[:min_pos]
        
        # 移除首尾空格
        return command.strip()
    
    def check_file_permissions(self, path):
        """检查文件权限"""
        if not os.path.exists(path):
            return False
        return os.access(path, os.X_OK)