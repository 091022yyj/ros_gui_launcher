#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度模块
- 定时启动任务
- 支持一次性任务和周期性任务
"""
import os
import json
import datetime
from threading import Timer


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or os.path.dirname(__file__)
        self.schedules_file = os.path.join(self.config_dir, "schedules.json")
        self.schedules = {}
        self.timers = {}
        self.callbacks = {}
        self._load_schedules()
    
    def _load_schedules(self):
        """加载调度配置"""
        if os.path.exists(self.schedules_file):
            try:
                with open(self.schedules_file, "r", encoding="utf-8") as f:
                    self.schedules = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.schedules = {}
        else:
            self.schedules = {}
    
    def save_schedules(self):
        """保存调度配置"""
        try:
            with open(self.schedules_file, "w", encoding="utf-8") as f:
                json.dump(self.schedules, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
    
    def add_schedule(self, name, task_type, task_path, schedule_type="once",
                     run_time=None, interval=None, enabled=True):
        """添加调度任务"""
        schedule = {
            "name": name,
            "task_type": task_type,  # "launch" 或 "py"
            "task_path": task_path,
            "schedule_type": schedule_type,  # "once" 或 "repeat"
            "run_time": run_time,  # ISO格式时间字符串
            "interval": interval,  # 间隔秒数
            "enabled": enabled,
            "created_at": datetime.datetime.now().isoformat(),
            "last_run": None,
            "next_run": None,
        }
        
        self.schedules[name] = schedule
        self.save_schedules()
        return schedule
    
    def remove_schedule(self, name):
        """移除调度任务"""
        if name in self.schedules:
            # 取消定时器
            if name in self.timers:
                self.timers[name].cancel()
                del self.timers[name]
            
            del self.schedules[name]
            self.save_schedules()
            return True
        return False
    
    def enable_schedule(self, name):
        """启用调度任务"""
        if name in self.schedules:
            self.schedules[name]["enabled"] = True
            self.save_schedules()
            return True
        return False
    
    def disable_schedule(self, name):
        """禁用调度任务"""
        if name in self.schedules:
            self.schedules[name]["enabled"] = False
            # 取消定时器
            if name in self.timers:
                self.timers[name].cancel()
                del self.timers[name]
            self.save_schedules()
            return True
        return False
    
    def get_schedule(self, name):
        """获取调度任务"""
        return self.schedules.get(name)
    
    def get_all_schedules(self):
        """获取所有调度任务"""
        return self.schedules
    
    def get_schedule_list(self):
        """获取调度任务列表"""
        schedules = []
        for name, schedule in self.schedules.items():
            schedules.append({
                "name": name,
                "task_type": schedule.get("task_type", ""),
                "task_path": schedule.get("task_path", ""),
                "schedule_type": schedule.get("schedule_type", "once"),
                "run_time": schedule.get("run_time", ""),
                "interval": schedule.get("interval"),
                "enabled": schedule.get("enabled", True),
                "last_run": schedule.get("last_run"),
                "next_run": schedule.get("next_run"),
            })
        return schedules
    
    def register_callback(self, name, callback):
        """注册回调函数"""
        self.callbacks[name] = callback
    
    def start_schedule(self, name):
        """启动调度任务"""
        schedule = self.schedules.get(name)
        if not schedule or not schedule.get("enabled"):
            return False
        
        callback = self.callbacks.get(name)
        if not callback:
            return False
        
        schedule_type = schedule.get("schedule_type", "once")
        
        if schedule_type == "once":
            # 一次性任务
            run_time_str = schedule.get("run_time")
            if run_time_str:
                run_time = datetime.datetime.fromisoformat(run_time_str)
                delay = (run_time - datetime.datetime.now()).total_seconds()
                if delay > 0:
                    timer = Timer(delay, self._run_task, args=[name])
                    self.timers[name] = timer
                    timer.start()
                    schedule["next_run"] = run_time.isoformat()
                    self.save_schedules()
                    return True
        elif schedule_type == "repeat":
            # 周期性任务
            interval = schedule.get("interval", 3600)
            timer = Timer(interval, self._run_task, args=[name])
            self.timers[name] = timer
            timer.start()
            
            next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval)
            schedule["next_run"] = next_run.isoformat()
            self.save_schedules()
            return True
        
        return False
    
    def _run_task(self, name):
        """执行任务"""
        schedule = self.schedules.get(name)
        if not schedule:
            return
        
        callback = self.callbacks.get(name)
        if callback:
            callback(schedule)
        
        # 更新最后运行时间
        schedule["last_run"] = datetime.datetime.now().isoformat()
        
        # 如果是一次性任务，禁用它
        if schedule.get("schedule_type") == "once":
            schedule["enabled"] = False
            schedule["next_run"] = None
        else:
            # 周期性任务，设置下一次运行时间
            interval = schedule.get("interval", 3600)
            next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval)
            schedule["next_run"] = next_run.isoformat()
            
            # 重新启动定时器
            timer = Timer(interval, self._run_task, args=[name])
            self.timers[name] = timer
            timer.start()
        
        self.save_schedules()
    
    def stop_all(self):
        """停止所有调度任务"""
        for name, timer in self.timers.items():
            timer.cancel()
        self.timers.clear()
    
    def start_all_enabled(self):
        """启动所有启用的调度任务"""
        for name, schedule in self.schedules.items():
            if schedule.get("enabled"):
                self.start_schedule(name)
