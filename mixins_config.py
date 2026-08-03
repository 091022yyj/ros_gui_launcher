#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mixins_config.py - ConfigMixin
由launcher_gui.py自动拆分生成,功能不变
"""
import os
import platform
import json
import datetime
import webbrowser
import subprocess
import traceback
from constants import (BASE_DIR, CONFIG_FILE, LOG_DIR, VERSION, DEFAULT_CONFIG,
                      MAX_RESTARTS, COL_STATUS, COL_PATH, COL_ARGS, COL_RESTART,
                      COL_AUTOSTART, COL_OPS, normalize_task)
from PyQt5.QtCore import Qt, QProcess, QTimer, QRectF
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog,
                             QGroupBox, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QAbstractItemView, QMessageBox,
                             QHeaderView, QSpinBox, QListWidgetItem, QComboBox,
                             QShortcut, QInputDialog, QTreeWidgetItem)


class ConfigMixin:
    """MainWindow功能mixin"""

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = dict(DEFAULT_CONFIG)
                merged.update(cfg)
                return merged
        except (OSError, ValueError):
            # 配置文件损坏时备份一份,避免反复报错
            try:
                os.replace(CONFIG_FILE, CONFIG_FILE + ".bak")
            except OSError:
                pass
            return dict(DEFAULT_CONFIG)

    def save_config(self):
        if not hasattr(self, "launch_table") or self._loading:
            return
        self.config["ros_setup"] = self.ros_setup_edit.text().strip()
        self.config["ws_setup"] = self.ws_setup_edit.text().strip()
        spin = self.launch_table.property("delay_spin")
        if spin:
            self.config["start_delay"] = spin.value()
        self.config["launch_files"] = [
            t.to_dict() for _, t, _ in self._rows_of(self.launch_table)]
        self.config["py_files"] = [
            t.to_dict() for _, t, _ in self._rows_of(self.py_table)]
        try:
            # 原子写入:先写临时文件再替换,防止中途崩溃损坏配置
            tmp = CONFIG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            os.replace(tmp, CONFIG_FILE)
        except OSError as e:
            self.log("保存配置失败: %s" % e)

    def _init_log_file(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            name = "launcher-%s.log" % datetime.date.today().isoformat()
            self._log_file = open(os.path.join(LOG_DIR, name), "a", encoding="utf-8")
        except OSError:
            self._log_file = None

    def log(self, text):
        if hasattr(self, 'log_view') and self.log_view is not None:
            self.log_view.appendPlainText(text)
        if hasattr(self, '_status_label'):
            self._status_label.setText(text[-60:])
        if self._log_file:
            try:
                stamp = datetime.datetime.now().strftime("%H:%M:%S")
                self._log_file.write("[%s] %s\n" % (stamp, text))
                self._log_file.flush()
            except OSError:
                pass

    def browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", os.path.expanduser("~"), "所有文件 (*)")
        if path:
            line_edit.setText(path)
            self.save_config()

    def closeEvent(self, event):
        # 关闭窗口前停掉所有进程
        for kind in ("launch", "py"):
            for r, task, _ in self._rows_of(self._table_of(kind)):
                task.stop()
        self.save_config()
        if self._log_file:
            self._log_file.close()
        event.accept()

    def _validate_path(self, path):
        """验证路径安全性"""
        return self.security.validate_path(path)

    def _sanitize_command(self, command):
        """清理命令"""
        return self.security.sanitize_command(command)

    def _check_platform(self):
        """检查平台兼容性"""
        system = platform.system()
        if system not in ["Linux", "Windows", "Darwin"]:
            print(f"警告：未测试的平台 {system}")
        return system

    def import_config(self):
        """导入配置"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", os.path.expanduser("~"),
            "JSON 文件 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_config = json.load(f)
            # 验证配置格式
            if "ros_setup" not in new_config:
                QMessageBox.warning(self, "格式错误", "配置文件格式不正确")
                return
            # 备份当前配置
            self.export_config(backup=True)
            # 应用新配置
            self.config.update(new_config)
            self.ros_setup_edit.setText(self.config.get("ros_setup", ""))
            self.ws_setup_edit.setText(self.config.get("ws_setup", ""))
            self.save_config()
            QMessageBox.information(self, "导入成功", "配置已导入，请重启程序以完全应用")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def export_config(self, backup=False):
        """导出配置"""
        if backup:
            path = CONFIG_FILE + ".backup"
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "导出配置文件", os.path.expanduser("~/config_backup.json"),
                "JSON 文件 (*.json)")
            if not path:
                return
        try:
            self.save_config()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            if not backup:
                QMessageBox.information(self, "导出成功", f"配置已导出到:\n{path}")
            self.log("配置已导出到: %s" % path)
        except Exception as e:
            if not backup:
                QMessageBox.critical(self, "导出失败", str(e))

    def check_update(self):
        """检查更新"""
        self.log("正在检查更新...")
        
        # 读取更新配置
        config_path = os.path.join(BASE_DIR, "update_config.json")
        self.log("配置路径: %s" % config_path)
        self.log("文件存在: %s" % os.path.exists(config_path))
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    update_config = json.load(f)
                repo_owner = update_config.get("repo_owner", "")
                repo_name = update_config.get("repo_name", "")
                self.log("repo_owner: %s, repo_name: %s" % (repo_owner, repo_name))
            except Exception as e:
                self.log("读取配置失败: %s" % str(e))
                repo_owner = ""
                repo_name = ""
        else:
            repo_owner = ""
            repo_name = ""
        
        if not repo_owner or not repo_name:
            QMessageBox.information(self, "检查更新", 
                "未配置更新服务器。请编辑 update_config.json 文件。\n路径: %s" % config_path)
            return
        
        # 设置更新服务器
        self.updater.set_update_server(f"https://api.github.com/repos/{repo_owner}/{repo_name}")
        
        # 在后台线程中检查更新(不阻塞界面)
        self._run_async(
            lambda: self.updater.check_for_updates(),
            self._on_update_check_done
        )

    def _on_update_check_done(self, result):
        """更新检查完成回调(区分: 有更新/已最新/连接失败)"""
        try:
            # 后台线程异常包装格式
            if result is None:
                QMessageBox.warning(self, "检查更新", "无法连接到更新服务器(无响应)")
                return
            if isinstance(result, dict) and result.get("success") is False:
                QMessageBox.warning(self, "检查更新", f"无法连接到更新服务器:\n{result.get('error', '未知错误')}")
                return
            if not result.get("ok"):
                QMessageBox.warning(self, "检查更新", f"无法连接到更新服务器:\n{result.get('error', '未知错误')}")
                return
            
            data = result.get("data") or {}
            if "tag_name" in data:
                latest_version = data["tag_name"].lstrip("v")
                if self.updater.compare_versions(VERSION, latest_version) < 0:
                    reply = QMessageBox.question(
                        self, "发现新版本",
                        f"发现新版本 {latest_version}，当前版本 {VERSION}\n\n"
                        f"更新说明:\n{data.get('body', '无')}\n\n"
                        f"是否打开下载页面？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        import webbrowser
                        webbrowser.open(data.get("html_url", ""))
                else:
                    QMessageBox.information(self, "检查更新", f"当前已是最新版本 (v{VERSION})")
            else:
                QMessageBox.information(self, "检查更新", f"当前已是最新版本 (v{VERSION})")
        except Exception as e:
            QMessageBox.warning(self, "检查更新失败", f"检查更新出错:\n{str(e)}")

    def _download_update(self, release_info):
        """下载更新"""
        self.log("开始下载更新...")
        import webbrowser
        # 打开浏览器让用户手动下载
        if "assets" in release_info and release_info["assets"]:
            download_url = release_info["assets"][0].get("browser_download_url", "")
            if download_url:
                webbrowser.open(download_url)
        else:
            webbrowser.open(release_info.get("html_url", ""))
