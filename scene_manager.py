#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景管理模块
- 保存/加载启动场景
- 支持场景切换
- 支持场景导入导出
"""
import os
import json
import datetime


class SceneManager:
    """场景管理器"""
    
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or os.path.dirname(__file__)
        self.scenes_file = os.path.join(self.config_dir, "scenes.json")
        self.scenes = {}
        self.current_scene = None
        self._load_scenes()
    
    def _load_scenes(self):
        """加载场景配置"""
        if os.path.exists(self.scenes_file):
            try:
                with open(self.scenes_file, "r", encoding="utf-8") as f:
                    self.scenes = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.scenes = {}
        else:
            self.scenes = {}
    
    def save_scenes(self):
        """保存场景配置"""
        try:
            with open(self.scenes_file, "w", encoding="utf-8") as f:
                json.dump(self.scenes, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
    
    def create_scene(self, name, description="", launch_files=None, py_files=None, 
                     ros_setup="", ws_setup="", start_delay=3):
        """创建新场景"""
        scene = {
            "name": name,
            "description": description,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "launch_files": launch_files or [],
            "py_files": py_files or [],
            "ros_setup": ros_setup,
            "ws_setup": ws_setup,
            "start_delay": start_delay,
        }
        self.scenes[name] = scene
        self.save_scenes()
        return scene
    
    def update_scene(self, name, **kwargs):
        """更新场景"""
        if name not in self.scenes:
            return None
        
        scene = self.scenes[name]
        for key, value in kwargs.items():
            if key in scene:
                scene[key] = value
        
        scene["updated_at"] = datetime.datetime.now().isoformat()
        self.scenes[name] = scene
        self.save_scenes()
        return scene
    
    def delete_scene(self, name):
        """删除场景"""
        if name in self.scenes:
            del self.scenes[name]
            if self.current_scene == name:
                self.current_scene = None
            self.save_scenes()
            return True
        return False
    
    def get_scene(self, name):
        """获取场景"""
        return self.scenes.get(name)
    
    def get_all_scenes(self):
        """获取所有场景"""
        return self.scenes
    
    def get_scene_list(self):
        """获取场景列表"""
        scenes = []
        for name, scene in self.scenes.items():
            scenes.append({
                "name": name,
                "description": scene.get("description", ""),
                "launch_count": len(scene.get("launch_files", [])),
                "py_count": len(scene.get("py_files", [])),
                "created_at": scene.get("created_at", ""),
                "updated_at": scene.get("updated_at", ""),
            })
        return scenes
    
    def set_current_scene(self, name):
        """设置当前场景"""
        if name in self.scenes or name is None:
            self.current_scene = name
            return True
        return False
    
    def get_current_scene(self):
        """获取当前场景"""
        if self.current_scene:
            return self.scenes.get(self.current_scene)
        return None
    
    def apply_scene(self, name):
        """应用场景配置"""
        scene = self.scenes.get(name)
        if not scene:
            return None
        
        self.current_scene = name
        return {
            "launch_files": scene.get("launch_files", []),
            "py_files": scene.get("py_files", []),
            "ros_setup": scene.get("ros_setup", ""),
            "ws_setup": scene.get("ws_setup", ""),
            "start_delay": scene.get("start_delay", 3),
        }
    
    def export_scene(self, name, output_file):
        """导出场景"""
        scene = self.scenes.get(name)
        if not scene:
            return False
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({name: scene}, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False
    
    def import_scene(self, input_file):
        """导入场景"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                imported = json.load(f)
            
            for name, scene in imported.items():
                if name in self.scenes:
                    # 重命名避免冲突
                    new_name = f"{name}_{datetime.datetime.now().strftime('%H%M%S')}"
                    self.scenes[new_name] = scene
                else:
                    self.scenes[name] = scene
            
            self.save_scenes()
            return True
        except (OSError, json.JSONDecodeError):
            return False
    
    def duplicate_scene(self, name, new_name):
        """复制场景"""
        scene = self.scenes.get(name)
        if not scene or new_name in self.scenes:
            return False
        
        new_scene = json.loads(json.dumps(scene))
        new_scene["name"] = new_name
        new_scene["created_at"] = datetime.datetime.now().isoformat()
        new_scene["updated_at"] = datetime.datetime.now().isoformat()
        
        self.scenes[new_name] = new_scene
        self.save_scenes()
        return True
    
    def add_launch_to_scene(self, scene_name, launch_file):
        """向场景添加launch文件"""
        scene = self.scenes.get(scene_name)
        if not scene:
            return False
        
        launch_files = scene.get("launch_files", [])
        if launch_file not in launch_files:
            launch_files.append(launch_file)
            scene["launch_files"] = launch_files
            scene["updated_at"] = datetime.datetime.now().isoformat()
            self.save_scenes()
        
        return True
    
    def remove_launch_from_scene(self, scene_name, launch_file):
        """从场景移除launch文件"""
        scene = self.scenes.get(scene_name)
        if not scene:
            return False
        
        launch_files = scene.get("launch_files", [])
        if launch_file in launch_files:
            launch_files.remove(launch_file)
            scene["launch_files"] = launch_files
            scene["updated_at"] = datetime.datetime.now().isoformat()
            self.save_scenes()
        
        return True
    
    def add_py_to_scene(self, scene_name, py_file):
        """向场景添加Python文件"""
        scene = self.scenes.get(scene_name)
        if not scene:
            return False
        
        py_files = scene.get("py_files", [])
        if py_file not in py_files:
            py_files.append(py_file)
            scene["py_files"] = py_files
            scene["updated_at"] = datetime.datetime.now().isoformat()
            self.save_scenes()
        
        return True
    
    def remove_py_from_scene(self, scene_name, py_file):
        """从场景移除Python文件"""
        scene = self.scenes.get(scene_name)
        if not scene:
            return False
        
        py_files = scene.get("py_files", [])
        if py_file in py_files:
            py_files.remove(py_file)
            scene["py_files"] = py_files
            scene["updated_at"] = datetime.datetime.now().isoformat()
            self.save_scenes()
        
        return True
