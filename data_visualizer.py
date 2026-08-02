#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据可视化模块
- CPU/内存历史趋势图
- 简单图表显示
"""
import os
import json
import time
from datetime import datetime
from collections import deque


class DataVisualizer:
    """数据可视化器"""
    
    def __init__(self, max_history=100):
        self.max_history = max_history
        self.cpu_history = deque(maxlen=max_history)
        self.mem_history = deque(maxlen=max_history)
        self.time_history = deque(maxlen=max_history)
    
    def add_data_point(self, cpu_percent, mem_percent):
        """添加数据点"""
        self.cpu_history.append(cpu_percent)
        self.mem_history.append(mem_percent)
        self.time_history.append(datetime.now().strftime("%H:%M:%S"))
    
    def get_history_data(self):
        """获取历史数据"""
        return {
            "time": list(self.time_history),
            "cpu": list(self.cpu_history),
            "memory": list(self.mem_history),
        }
    
    def generate_ascii_chart(self, data, width=60, height=20):
        """生成ASCII图表"""
        if not data:
            return "无数据"
        
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val > min_val else 1
        
        chart = []
        for row in range(height, -1, -1):
            threshold = min_val + (range_val * row / height)
            line = ""
            for val in data:
                if val >= threshold:
                    line += "█"
                else:
                    line += " "
            chart.append(f"{threshold:6.1f}|{line}|")
        
        return "\n".join(chart)
    
    def get_cpu_chart(self):
        """获取CPU使用率图表"""
        chart_data = list(self.cpu_history)
        return self.generate_ascii_chart(chart_data)
    
    def get_memory_chart(self):
        """获取内存使用率图表"""
        chart_data = list(self.mem_history)
        return self.generate_ascii_chart(chart_data)
    
    def get_statistics(self):
        """获取统计数据"""
        if not self.cpu_history:
            return {"error": "无数据"}
        
        return {
            "cpu": {
                "current": self.cpu_history[-1] if self.cpu_history else 0,
                "average": sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0,
                "max": max(self.cpu_history) if self.cpu_history else 0,
                "min": min(self.cpu_history) if self.cpu_history else 0,
            },
            "memory": {
                "current": self.mem_history[-1] if self.mem_history else 0,
                "average": sum(self.mem_history) / len(self.mem_history) if self.mem_history else 0,
                "max": max(self.mem_history) if self.mem_history else 0,
                "min": min(self.mem_history) if self.mem_history else 0,
            },
            "samples": len(self.cpu_history),
        }
    
    def save_history(self, output_file):
        """保存历史数据"""
        data = self.get_history_data()
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def load_history(self, input_file):
        """加载历史数据"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.time_history = deque(data.get("time", []), maxlen=self.max_history)
            self.cpu_history = deque(data.get("cpu", []), maxlen=self.max_history)
            self.mem_history = deque(data.get("memory", []), maxlen=self.max_history)
            return True
        except Exception:
            return False
