#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统模块
- 支持第三方插件扩展
- 插件加载和管理
"""
import os
import sys
import json
import importlib.util


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dir=None, config_dir=None):
        self.plugin_dir = plugin_dir or os.path.join(os.path.dirname(__file__), "plugins")
        self.config_dir = config_dir or os.path.dirname(__file__)
        self.plugins_file = os.path.join(self.config_dir, "plugins.json")
        self.plugins = {}
        self.loaded_plugins = {}
        self._ensure_plugin_dir()
        self._load_plugins_config()
    
    def _ensure_plugin_dir(self):
        """确保插件目录存在"""
        os.makedirs(self.plugin_dir, exist_ok=True)
    
    def _load_plugins_config(self):
        """加载插件配置"""
        if os.path.exists(self.plugins_file):
            try:
                with open(self.plugins_file, "r", encoding="utf-8") as f:
                    self.plugins = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.plugins = {}
        else:
            self.plugins = {}
    
    def save_plugins_config(self):
        """保存插件配置"""
        try:
            with open(self.plugins_file, "w", encoding="utf-8") as f:
                json.dump(self.plugins, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
    
    def discover_plugins(self):
        """发现可用插件"""
        discovered = []
        
        if not os.path.exists(self.plugin_dir):
            return discovered
        
        for item in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, item)
            
            # 检查是否是目录（插件包）
            if os.path.isdir(plugin_path):
                init_file = os.path.join(plugin_path, "__init__.py")
                if os.path.exists(init_file):
                    discovered.append({
                        "name": item,
                        "path": plugin_path,
                        "type": "package"
                    })
            
            # 检查是否是Python文件
            elif item.endswith(".py") and not item.startswith("_"):
                discovered.append({
                    "name": item[:-3],
                    "path": plugin_path,
                    "type": "module"
                })
        
        return discovered
    
    def load_plugin(self, plugin_name):
        """加载插件"""
        if plugin_name in self.loaded_plugins:
            return {"success": True, "plugin": self.loaded_plugins[plugin_name]}
        
        # 查找插件
        discovered = self.discover_plugins()
        plugin_info = None
        
        for p in discovered:
            if p["name"] == plugin_name:
                plugin_info = p
                break
        
        if not plugin_info:
            return {"success": False, "error": f"插件 '{plugin_name}' 未找到"}
        
        try:
            if plugin_info["type"] == "module":
                # 加载模块
                spec = importlib.util.spec_from_file_location(
                    plugin_name, plugin_info["path"]
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # 加载包
                spec = importlib.util.spec_from_file_location(
                    plugin_name,
                    os.path.join(plugin_info["path"], "__init__.py")
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            # 检查插件接口
            if not hasattr(module, "plugin_info"):
                return {"success": False, "error": "插件缺少 plugin_info 函数"}
            
            info = module.plugin_info()
            
            self.loaded_plugins[plugin_name] = {
                "module": module,
                "info": info,
                "path": plugin_info["path"]
            }
            
            # 更新配置
            self.plugins[plugin_name] = {
                "enabled": True,
                "path": plugin_info["path"]
            }
            self.save_plugins_config()
            
            return {"success": True, "plugin": self.loaded_plugins[plugin_name]}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def unload_plugin(self, plugin_name):
        """卸载插件"""
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            
            # 调用插件的卸载函数
            module = plugin.get("module")
            if module and hasattr(module, "plugin_unload"):
                try:
                    module.plugin_unload()
                except Exception:
                    pass
            
            del self.loaded_plugins[plugin_name]
            return True
        return False
    
    def get_plugin_info(self, plugin_name):
        """获取插件信息"""
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name].get("info", {})
        return None
    
    def get_loaded_plugins(self):
        """获取已加载的插件"""
        plugins = []
        for name, plugin in self.loaded_plugins.items():
            plugins.append({
                "name": name,
                "info": plugin.get("info", {}),
                "path": plugin.get("path", "")
            })
        return plugins
    
    def call_plugin_function(self, plugin_name, function_name, *args, **kwargs):
        """调用插件函数"""
        if plugin_name not in self.loaded_plugins:
            return {"success": False, "error": f"插件 '{plugin_name}' 未加载"}
        
        plugin = self.loaded_plugins[plugin_name]
        module = plugin.get("module")
        
        if not module or not hasattr(module, function_name):
            return {"success": False, "error": f"函数 '{function_name}' 不存在"}
        
        try:
            func = getattr(module, function_name)
            result = func(*args, **kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def enable_plugin(self, plugin_name):
        """启用插件"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name]["enabled"] = True
            self.save_plugins_config()
            return True
        return False
    
    def disable_plugin(self, plugin_name):
        """禁用插件"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name]["enabled"] = False
            self.save_plugins_config()
            return True
        return False
    
    def install_plugin(self, plugin_path):
        """安装插件"""
        if not os.path.exists(plugin_path):
            return {"success": False, "error": "插件路径不存在"}
        
        plugin_name = os.path.basename(plugin_path)
        if plugin_path.endswith(".py"):
            plugin_name = plugin_name[:-3]
        
        dest_path = os.path.join(self.plugin_dir, os.path.basename(plugin_path))
        
        try:
            import shutil
            if os.path.isdir(plugin_path):
                shutil.copytree(plugin_path, dest_path)
            else:
                shutil.copy2(plugin_path, dest_path)
            
            return {"success": True, "name": plugin_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def uninstall_plugin(self, plugin_name):
        """卸载插件"""
        # 先卸载
        self.unload_plugin(plugin_name)
        
        # 查找插件路径
        plugin_info = self.plugins.get(plugin_name, {})
        plugin_path = plugin_info.get("path", "")
        
        if plugin_path and os.path.exists(plugin_path):
            try:
                import shutil
                if os.path.isdir(plugin_path):
                    shutil.rmtree(plugin_path)
                else:
                    os.remove(plugin_path)
            except Exception:
                pass
        
        # 移除配置
        if plugin_name in self.plugins:
            del self.plugins[plugin_name]
            self.save_plugins_config()
        
        return True
