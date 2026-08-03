import json
import os
import shutil
from pathlib import Path

DEFAULT_CONFIG = {
    "ros_setup": "/opt/ros/noetic/setup.bash",
    "ws_setup": "",
    "start_delay": 3,
    "launch_files": [],
    "py_files": [],
}

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.backup_dir = self.config_path.parent / "config_backups"

    def load(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                merged = dict(DEFAULT_CONFIG)
                merged.update(config)
                return merged
        except (OSError, ValueError):
            # 配置文件损坏时尝试从备份恢复
            return self._load_from_backup()

    def save(self, config):
        """保存配置文件（原子写入）"""
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # 原子写入
            tmp_path = self.config_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            # 替换原文件
            os.replace(tmp_path, self.config_path)

            # 创建备份
            self._create_backup(config)

            return True
        except OSError:
            return False

    def export_config(self, export_path):
        """导出配置到文件"""
        try:
            config = self.load()
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def import_config(self, import_path):
        """从文件导入配置"""
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                return False
            with open(import_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return self.save(config)
        except:
            return False

    def _load_from_backup(self):
        """从备份加载配置"""
        try:
            if self.backup_dir.exists():
                backups = sorted(self.backup_dir.glob("config_*.json"))
                if backups:
                    with open(backups[-1], 'r', encoding='utf-8') as f:
                        return json.load(f)
        except:
            pass
        return dict(DEFAULT_CONFIG)

    def _create_backup(self, config):
        """创建配置备份"""
        try:
            self.backup_dir.mkdir(exist_ok=True)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"config_{timestamp}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
