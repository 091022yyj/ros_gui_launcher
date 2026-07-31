# updater.py
import os
import shutil
import datetime
import requests
from packaging import version

class Updater:
    def __init__(self, current_version="1.2.0"):
        self.current_version = current_version
        self.update_server = None
        self.update_channel = "stable"
        self.backup_dir = "backups"
    
    def set_update_server(self, server_url):
        self.update_server = server_url
    
    def compare_versions(self, v1, v2):
        """比较版本号，返回-1, 0, 1"""
        try:
            ver1 = version.parse(v1)
            ver2 = version.parse(v2)
            if ver1 < ver2:
                return -1
            elif ver1 > ver2:
                return 1
            else:
                return 0
        except:
            return 0
    
    def check_for_updates(self):
        """检查是否有更新"""
        if not self.update_server:
            return None
        
        try:
            response = requests.get(f"{self.update_server}/latest.json", timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return None
    
    def download_update(self, update_url, save_path):
        """下载更新包"""
        try:
            response = requests.get(update_url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except:
            pass
        
        return False
    
    def create_backup(self):
        """创建当前版本备份"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns('backups', '__pycache__', '.git'))
            return backup_path
        except:
            return None
    
    def apply_update(self, update_path):
        """应用更新"""
        backup_path = None
        try:
            # 备份当前版本
            backup_path = self.create_backup()
            
            # 应用更新
            # 这里需要根据更新包格式实现具体逻辑
            
            return True
        except:
            # 回滚
            if backup_path:
                self.rollback(backup_path)
            return False
    
    def rollback(self, backup_path):
        """回滚到备份版本"""
        try:
            # 清除当前文件
            for item in os.listdir('.'):
                if item not in ['backups', '.git', 'config.json']:
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                    else:
                        os.remove(item)
            
            # 恢复备份
            for item in os.listdir(backup_path):
                src = os.path.join(backup_path, item)
                dst = os.path.join('.', item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            return True
        except:
            return False