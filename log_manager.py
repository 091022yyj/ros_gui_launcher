#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
- 按任务分文件存储日志
- 支持日志过滤和搜索
- 支持日志导出
"""
import os
import datetime
import re
from collections import defaultdict


class LogManager:
    """日志管理器"""
    
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.task_logs = {}  # {task_name: log_file_handle}
        self.log_files = {}  # {task_name: log_file_path}
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        os.makedirs(self.log_dir, exist_ok=True)
    
    def _get_log_path(self, task_name, date=None):
        """获取日志文件路径"""
        if date is None:
            date = datetime.date.today().isoformat()
        # 清理任务名中的特殊字符
        safe_name = re.sub(r'[^\w\-.]', '_', task_name)
        return os.path.join(self.log_dir, f"{safe_name}_{date}.log")
    
    def start_task_log(self, task_name):
        """开始记录任务日志"""
        if task_name in self.task_logs:
            return
        
        log_path = self._get_log_path(task_name)
        try:
            log_file = open(log_path, "a", encoding="utf-8")
            self.task_logs[task_name] = log_file
            self.log_files[task_name] = log_path
        except OSError as e:
            print(f"无法打开日志文件 {log_path}: {e}")
    
    def stop_task_log(self, task_name):
        """停止记录任务日志"""
        if task_name in self.task_logs:
            try:
                self.task_logs[task_name].close()
            except OSError:
                pass
            del self.task_logs[task_name]
            if task_name in self.log_files:
                del self.log_files[task_name]
    
    def write_log(self, task_name, text):
        """写入任务日志"""
        if task_name in self.task_logs:
            try:
                stamp = datetime.datetime.now().strftime("%H:%M:%S")
                self.task_logs[task_name].write(f"[{stamp}] {text}\n")
                self.task_logs[task_name].flush()
            except OSError:
                pass
    
    def get_task_log_path(self, task_name):
        """获取任务的日志文件路径"""
        return self.log_files.get(task_name)
    
    def get_all_log_files(self):
        """获取所有日志文件"""
        log_files = []
        if os.path.exists(self.log_dir):
            for f in os.listdir(self.log_dir):
                if f.endswith(".log"):
                    log_files.append(os.path.join(self.log_dir, f))
        return sorted(log_files)
    
    def get_task_log_files(self, task_name):
        """获取指定任务的所有日志文件"""
        log_files = []
        safe_name = re.sub(r'[^\w\-.]', '_', task_name)
        if os.path.exists(self.log_dir):
            for f in os.listdir(self.log_dir):
                if f.startswith(safe_name) and f.endswith(".log"):
                    log_files.append(os.path.join(self.log_dir, f))
        return sorted(log_files)
    
    def read_log_file(self, file_path, max_lines=1000):
        """读取日志文件内容"""
        lines = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-max_lines:]
        except OSError:
            pass
        return lines
    
    def filter_logs(self, lines, keyword=None, level=None):
        """过滤日志"""
        filtered = []
        for line in lines:
            if keyword and keyword.lower() not in line.lower():
                continue
            if level:
                level_patterns = {
                    "ERROR": r"\[ERROR\]|错误|error",
                    "WARNING": r"\[WARN\]|警告|warning",
                    "INFO": r"\[INFO\]|信息|info",
                    "DEBUG": r"\[DEBUG\]|调试|debug",
                }
                if level in level_patterns:
                    if not re.search(level_patterns[level], line, re.IGNORECASE):
                        continue
            filtered.append(line)
        return filtered
    
    def search_logs(self, keyword, log_dir=None):
        """搜索所有日志文件"""
        search_dir = log_dir or self.log_dir
        results = []
        
        if not os.path.exists(search_dir):
            return results
        
        for f in os.listdir(search_dir):
            if not f.endswith(".log"):
                continue
            file_path = os.path.join(search_dir, f)
            try:
                with open(file_path, "r", encoding="utf-8") as log_file:
                    for i, line in enumerate(log_file, 1):
                        if keyword.lower() in line.lower():
                            results.append({
                                "file": f,
                                "line": i,
                                "content": line.strip()
                            })
            except OSError:
                continue
        
        return results
    
    def export_logs(self, output_file, task_name=None, start_date=None, end_date=None):
        """导出日志"""
        log_files = self.get_all_log_files()
        
        if task_name:
            log_files = [f for f in log_files if task_name in os.path.basename(f)]
        
        if start_date:
            log_files = [f for f in log_files if os.path.basename(f) >= start_date]
        
        if end_date:
            log_files = [f for f in log_files if os.path.basename(f) <= end_date]
        
        try:
            with open(output_file, "w", encoding="utf-8") as out:
                for log_file in log_files:
                    out.write(f"\n{'='*60}\n")
                    out.write(f"日志文件: {os.path.basename(log_file)}\n")
                    out.write(f"{'='*60}\n\n")
                    with open(log_file, "r", encoding="utf-8") as f:
                        out.write(f.read())
            return True
        except OSError:
            return False
    
    def cleanup_old_logs(self, days=30):
        """清理旧日志文件"""
        if not os.path.exists(self.log_dir):
            return
        
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
        
        for f in os.listdir(self.log_dir):
            if not f.endswith(".log"):
                continue
            file_path = os.path.join(self.log_dir, f)
            try:
                file_date = datetime.date.fromisoformat(f.split("_")[0])
                if file_date < cutoff_date:
                    os.remove(file_path)
            except (ValueError, OSError):
                continue
    
    def close_all(self):
        """关闭所有日志文件"""
        for task_name in list(self.task_logs.keys()):
            self.stop_task_log(task_name)
