# updater.py
import requests
from packaging import version

class Updater:
    def __init__(self, current_version="1.2.0"):
        self.current_version = current_version
        self.update_server = None
        self.update_channel = "stable"
    
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