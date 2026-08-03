#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mixins_monitor.py - MonitorMixin
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


class MonitorMixin:
    """MainWindow功能mixin"""

    def refresh_monitor(self):
        """刷新系统监控(异步,psutil放后台线程避免阻塞主界面)"""
        def worker():
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.2)
                mem = psutil.virtual_memory().percent
                return {"cpu": cpu, "mem": mem, "ok": True}
            except ImportError:
                return {"ok": False, "error": "psutil未安装"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        
        def on_done(result):
            if not result.get("ok"):
                self.cpu_label.setText("CPU: 获取失败")
                self.mem_label.setText("内存: 获取失败")
                return
            cpu = result["cpu"]
            mem = result["mem"]
            self.cpu_label.setText(f"CPU: {cpu:.1f}%")
            self.mem_label.setText(f"内存: {mem:.1f}%")
            if hasattr(self, 'trend_chart'):
                self.trend_chart.add_data_point("cpu", cpu)
                self.trend_chart.add_data_point("memory", mem)
            
            # 获取运行中的进程(在主线程,轻量)
            running_tasks = []
            for kind in ("launch", "py"):
                for r, task, _ in self._rows_of(self._table_of(kind)):
                    if task.is_running():
                        name = os.path.basename(task.path)
                        pid = task.process.processId() if task.process else "N/A"
                        running_tasks.append(f"● {name} (PID: {pid})")
            
            if running_tasks:
                self.proc_list.setPlainText("\n".join(running_tasks))
            else:
                self.proc_list.setPlainText("无运行中的进程")
        
        self._run_async(worker, on_done)

    def _load_history(self):
        """加载历史记录到列表"""
        if not hasattr(self, 'history_list'):
            return
        self.history_list.clear()
        history = self.config.get("history", [])
        for item in history[-50:]:  # 最多显示50条
            self.history_list.addItem(item)

    def _add_to_history(self, path):
        """添加文件到历史记录"""
        if not path:
            return
        history = self.config.get("history", [])
        # 避免重复
        if path in history:
            history.remove(path)
        history.append(path)
        # 最多保留100条
        if len(history) > 100:
            history = history[-100:]
        self.config["history"] = history
        self.save_config()
        # 更新UI
        if hasattr(self, 'history_list'):
            self.history_list.clear()
            for item in history[-50:]:
                self.history_list.addItem(item)

    def _on_history_clicked(self, item):
        """双击历史记录项"""
        path = item.text()
        if not os.path.exists(path):
            QMessageBox.warning(self, "文件不存在", f"文件已不存在:\n{path}")
            return
        
        # 根据文件类型添加到对应的表格
        if path.endswith('.launch'):
            kind = "launch"
        elif path.endswith('.py'):
            kind = "py"
        else:
            # 询问用户
            reply = QMessageBox.question(self, "选择类型",
                "该文件应添加到哪个类别？",
                QMessageBox.Yes | QMessageBox.No)
            kind = "launch" if reply == QMessageBox.Yes else "py"
        
        table = self._table_of(kind)
        # 检查是否已存在
        for r, task, _ in self._rows_of(table):
            if task.path == path:
                QMessageBox.information(self, "已存在", "该文件已在列表中")
                return
        
        self._add_row(table, normalize_task(path), kind)
        self.log(f"从历史记录加载: {path}")

    def _clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(self, "确认清空",
            "确定要清空所有历史记录吗？",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config["history"] = []
            self.save_config()
            if hasattr(self, 'history_list'):
                self.history_list.clear()
            self.log("历史记录已清空")

    def _update_progress(self, current, total):
        """更新进度条"""
        if hasattr(self, 'global_progress'):
            if total > 0:
                self.global_progress.setValue(int(current / total * 100))
                self.global_progress.show()
            else:
                self.global_progress.hide()

    def _load_scene_list(self):
        """加载场景列表"""
        if not hasattr(self, 'scene_list'):
            return
        self.scene_list.clear()
        scenes = self.scene_manager.get_scene_list()
        for scene in scenes:
            text = f"{scene['name']} ({scene['launch_count']}launch, {scene['py_count']}py)"
            self.scene_list.addItem(text)

    def _create_scene(self):
        """创建新场景"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "创建场景", "场景名称:")
        if ok and name:
            # 获取当前配置
            launch_files = [t.to_dict() for _, t, _ in self._rows_of(self.launch_table)]
            py_files = [t.to_dict() for _, t, _ in self._rows_of(self.py_table)]
            
            self.scene_manager.create_scene(
                name,
                launch_files=launch_files,
                py_files=py_files,
                ros_setup=self.ros_setup_edit.text(),
                ws_setup=self.ws_setup_edit.text(),
                start_delay=self.launch_table.property("delay_spin").value()
            )
            self._load_scene_list()
            self.log(f"创建场景: {name}")

    def _save_current_as_scene(self):
        """将当前配置保存为场景"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "保存场景", "场景名称:")
        if ok and name:
            launch_files = [t.to_dict() for _, t, _ in self._rows_of(self.launch_table)]
            py_files = [t.to_dict() for _, t, _ in self._rows_of(self.py_table)]
            
            self.scene_manager.create_scene(
                name,
                launch_files=launch_files,
                py_files=py_files,
                ros_setup=self.ros_setup_edit.text(),
                ws_setup=self.ws_setup_edit.text(),
                start_delay=self.launch_table.property("delay_spin").value()
            )
            self._load_scene_list()
            self.log(f"保存当前配置为场景: {name}")

    def _on_scene_clicked(self, item):
        """双击场景项"""
        scene_name = item.text().split(" (")[0]
        self._apply_scene_by_name(scene_name)

    def _apply_scene(self):
        """应用选中的场景"""
        current_item = self.scene_list.currentItem()
        if current_item:
            scene_name = current_item.text().split(" (")[0]
            self._apply_scene_by_name(scene_name)

    def _apply_scene_by_name(self, scene_name):
        """按名称应用场景"""
        config = self.scene_manager.apply_scene(scene_name)
        if not config:
            QMessageBox.warning(self, "错误", f"无法加载场景: {scene_name}")
            return
        
        # 清空当前列表
        self.launch_table.setRowCount(0)
        self.py_table.setRowCount(0)
        
        # 加载场景配置
        self.ros_setup_edit.setText(config.get("ros_setup", ""))
        self.ws_setup_edit.setText(config.get("ws_setup", ""))
        
        for entry in config.get("launch_files", []):
            self._add_row(self.launch_table, normalize_task(entry), "launch")
        
        for entry in config.get("py_files", []):
            self._add_row(self.py_table, normalize_task(entry), "py")
        
        delay_spin = self.launch_table.property("delay_spin")
        if delay_spin:
            delay_spin.setValue(config.get("start_delay", 3))
        
        self.config["current_scene"] = scene_name
        self.save_config()
        self.log(f"应用场景: {scene_name}")

    def _delete_scene(self):
        """删除场景"""
        current_item = self.scene_list.currentItem()
        if not current_item:
            return
        
        scene_name = current_item.text().split(" (")[0]
        reply = QMessageBox.question(self, "确认删除",
            f"确定要删除场景 '{scene_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.scene_manager.delete_scene(scene_name)
            self._load_scene_list()
            self.log(f"删除场景: {scene_name}")

    def _translate_text(self):
        """翻译文本"""
        text = self.translator_input.text().strip()
        if text:
            translated = self.translator.translate(text)
            self.translator_output.setText(translated)

    def _copy_translation(self):
        """复制翻译结果"""
        text = self.translator_output.text()
        if text:
            QApplication.clipboard().setText(text)
            self.log("翻译结果已复制到剪贴板")

    def _toggle_translation(self):
        """切换翻译功能"""
        enabled = self.translation_enabled_cb.isChecked()
        self.config["translation_enabled"] = enabled
        self.save_config()
        self.log(f"自动翻译: {'启用' if enabled else '禁用'}")

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if os.path.isfile(path):
                self._add_file_by_path(path)

    def _add_file_by_path(self, path):
        """根据路径添加文件"""
        if path.endswith('.launch'):
            kind = "launch"
        elif path.endswith('.py'):
            kind = "py"
        else:
            return
        
        table = self._table_of(kind)
        for r, task, _ in self._rows_of(table):
            if task.path == path:
                return
        
        self._add_row(table, normalize_task(path), kind)
        self._add_to_history(path)
        self.log(f"通过拖拽添加: {path}")

    def on_process_output(self, task, text):
        """进程输出回调（带日志分离）"""
        name = os.path.basename(task.path)
        
        # 写入任务日志
        self.log_manager.write_log(name, text)
        
        # 写入合并日志
        for line in text.rstrip("\n").splitlines():
            log_line = "[%s] %s" % (name, line)
            
            # 自动翻译错误信息
            if self.config.get("translation_enabled", True):
                log_line = self.translator.translate(log_line)
            
            self.log(log_line)

    def _refresh_ros_master(self):
        """刷新ROS主节点状态(异步)"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self.ros_master_status.setText("状态: 查询中...")
        def on_done(result):
            if result["running"]:
                self.ros_master_status.setText("状态: 运行中 ✓")
                self.ros_master_status.setStyleSheet("color: #66bb6a; font-weight: bold;")
            else:
                self.ros_master_status.setText("状态: 未运行 ✗")
                self.ros_master_status.setStyleSheet("color: #ef5350; font-weight: bold;")
        self._run_async(lambda: self.ros_monitor.check_ros_master(), on_done)

    def _refresh_ros_nodes(self):
        """刷新ROS节点列表(异步)"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self.node_tree.clear()
        self.node_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", ""]))
        def on_done(result):
            self.node_tree.clear()
            if result["error"]:
                item = QTreeWidgetItem(["错误: " + result["error"]])
                self.node_tree.addTopLevelItem(item)
                return
            for node in result["nodes"]:
                item = QTreeWidgetItem([node, "存活", "", ""])
                self.node_tree.addTopLevelItem(item)
            self.log(f"刷新节点列表: {len(result['nodes'])} 个节点")
        self._run_async(lambda: self.ros_monitor.get_ros_nodes(), on_done)

    def _show_node_info(self):
        """显示节点信息"""
        current_item = self.node_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return
        
        node_name = current_item.text(0)
        result = self.ros_monitor.get_node_info(node_name)
        
        if result["error"]:
            QMessageBox.warning(self, "错误", f"获取节点信息失败:\n{result['error']}")
            return
        
        info = result["info"]
        msg = f"节点: {info['name']}\n"
        msg += f"PID: {info['pid'] or '未知'}\n"
        msg += f"\n发布者 ({len(info['publishers'])}):\n"
        for pub in info['publishers'][:5]:
            msg += f"  - {pub}\n"
        msg += f"\n订阅者 ({len(info['subscribers'])}):\n"
        for sub in info['subscribers'][:5]:
            msg += f"  - {sub}\n"
        msg += f"\n服务 ({len(info['services'])}):\n"
        for svc in info['services'][:5]:
            msg += f"  - {svc}\n"
        
        QMessageBox.information(self, "节点信息", msg)

    def _refresh_ros_topics(self):
        """刷新ROS Topic列表(异步)"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self.topic_tree.clear()
        self.topic_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", ""]))
        def on_done(result):
            self.topic_tree.clear()
            if result["error"]:
                item = QTreeWidgetItem(["错误: " + result["error"]])
                self.topic_tree.addTopLevelItem(item)
                return
            for topic in result["topics"]:
                item = QTreeWidgetItem([topic, "", "", ""])
                self.topic_tree.addTopLevelItem(item)
        self._run_async(lambda: self.ros_monitor.get_ros_topics(), on_done)
        
        self.log(f"刷新Topic列表: {len(result['topics'])} 个话题")

    def _show_topic_info(self):
        """显示Topic信息"""
        current_item = self.topic_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个Topic")
            return
        
        topic_name = current_item.text(0)
        result = self.ros_monitor.get_topic_info(topic_name)
        
        if result["error"]:
            QMessageBox.warning(self, "错误", f"获取Topic信息失败:\n{result['error']}")
            return
        
        info = result["info"]
        msg = f"Topic: {info['name']}\n"
        msg += f"类型: {info['type'] or '未知'}\n"
        msg += f"\n发布者 ({len(info['publishers'])}):\n"
        for pub in info['publishers'][:5]:
            msg += f"  - {pub}\n"
        msg += f"\n订阅者 ({len(info['subscribers'])}):\n"
        for sub in info['subscribers'][:5]:
            msg += f"  - {sub}\n"
        
        QMessageBox.information(self, "Topic信息", msg)

    def _refresh_network(self):
        """刷新网络状态"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        
        master_uri = self.ros_monitor.get_ros_master_uri()
        master_status = self.ros_monitor.check_ros_master()
        
        info = f"ROS_MASTER_URI: {master_uri}\n"
        info += f"主节点状态: {'运行中' if master_status['running'] else '未运行'}\n"
        
        # 检查常用端口
        ports = [(11311, "ROS主节点"), (11312, "ROS节点")]
        for port, name in ports:
            is_open = self.ros_monitor.check_port_open("localhost", port)
            info += f"端口 {port} ({name}): {'开放' if is_open else '关闭'}\n"
        
        self.network_info.setPlainText(info)

    def _auto_refresh_ros_monitor(self):
        """自动刷新ROS监控(异步,防止定时器阻塞界面)"""
        # 更新ROS环境
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        
        def on_done(result):
            if result.get("running"):
                self.ros_master_status.setText("状态: 运行中 ✓")
                self.ros_master_status.setStyleSheet("color: #66bb6a; font-weight: bold;")
            else:
                self.ros_master_status.setText("状态: 未运行 ✗")
                self.ros_master_status.setStyleSheet("color: #ef5350; font-weight: bold;")
        
        self._run_async(
            lambda: self.ros_monitor.check_ros_master(),
            on_done
        )

    def _refresh_disk(self):
        """刷新磁盘信息(异步)"""
        self.disk_tree.clear()
        self.disk_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", "", "", ""]))
        def on_done(result):
            self.disk_tree.clear()
            if result["error"]:
                item = QTreeWidgetItem(["错误: " + result["error"]])
                self.disk_tree.addTopLevelItem(item)
                return
            for part in result["partitions"]:
                if "total" in part:
                    item = QTreeWidgetItem([
                        part["device"],
                        part["mountpoint"],
                        self.ros_monitor._format_size(part["total"]),
                        self.ros_monitor._format_size(part["used"]),
                        self.ros_monitor._format_size(part["free"]),
                        f"{part['percent']}%"
                    ])
                else:
                    item = QTreeWidgetItem([
                        part["device"],
                        part["mountpoint"],
                        part.get("size", "N/A"),
                        part.get("used", "N/A"),
                        part.get("available", "N/A"),
                        part.get("percent", "N/A")
                    ])
                self.disk_tree.addTopLevelItem(item)
        self._run_async(lambda: self.ros_monitor.get_disk_usage(), on_done)

    def _refresh_log_size(self):
        """刷新日志目录大小(异步)"""
        log_dir = os.path.join(BASE_DIR, "logs")
        self.log_size_label.setText("日志目录大小: 计算中...")
        def on_done(result):
            self.log_size_label.setText(f"日志目录大小: {result['size_human']}")
        self._run_async(
            lambda: self.ros_monitor.get_log_directory_size(log_dir),
            on_done
        )

    def _clean_old_logs(self):
        """清理旧日志"""
        reply = QMessageBox.question(self, "确认清理",
            "确定要清理30天前的日志文件吗？",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_manager.cleanup_old_logs(days=30)
            self._refresh_log_size()
            self.log("已清理旧日志文件")

    def _setup_hotkeys(self):
        """设置快捷键"""
        # F5 - 一键启动所有任务
        shortcut_start = QShortcut(QKeySequence("F5"), self)
        shortcut_start.activated.connect(self.start_everything)
        
        # F6 - 停止所有任务
        shortcut_stop = QShortcut(QKeySequence("F6"), self)
        shortcut_stop.activated.connect(self.stop_everything)
        
        # F7 - 启动选中的launch任务
        shortcut_start_launch = QShortcut(QKeySequence("F7"), self)
        shortcut_start_launch.activated.connect(lambda: self.start_selected("launch"))
        
        # F8 - 停止选中的launch任务
        shortcut_stop_launch = QShortcut(QKeySequence("F8"), self)
        shortcut_stop_launch.activated.connect(lambda: self.stop_selected("launch"))
        
        # Ctrl+L - 清空日志
        shortcut_clear_log = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_clear_log.activated.connect(self.log_view.clear)
        
        # Ctrl+S - 保存配置
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self.save_config)
        
        # Ctrl+R - 刷新监控
        shortcut_refresh = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut_refresh.activated.connect(self.refresh_monitor)

    def _load_config_list(self):
        """加载配置列表"""
        if not hasattr(self, 'config_combo'):
            return
        
        self.config_combo.clear()
        
        # 获取所有配置文件
        config_dir = os.path.join(BASE_DIR, "configs")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        # 添加默认配置
        self.config_combo.addItem("默认配置")
        
        # 添加其他配置文件
        for f in os.listdir(config_dir):
            if f.endswith(".json"):
                config_name = f[:-5]  # 移除.json
                self.config_combo.addItem(config_name)
        
        # 设置当前配置
        current_config = self.config.get("current_config", "默认配置")
        index = self.config_combo.findText(current_config)
        if index >= 0:
            self.config_combo.setCurrentIndex(index)

    def _on_config_changed(self, config_name):
        """配置切换"""
        if config_name == "默认配置":
            return
        
        config_file = os.path.join(BASE_DIR, "configs", f"{config_name}.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
                
                # 应用新配置
                self.config.update(new_config)
                self.ros_setup_edit.setText(self.config.get("ros_setup", ""))
                self.ws_setup_edit.setText(self.config.get("ws_setup", ""))
                
                # 清空并重新加载任务列表
                self.launch_table.setRowCount(0)
                self.py_table.setRowCount(0)
                
                for entry in self.config.get("launch_files", []):
                    self._add_row(self.launch_table, normalize_task(entry), "launch")
                
                for entry in self.config.get("py_files", []):
                    self._add_row(self.py_table, normalize_task(entry), "py")
                
                delay_spin = self.launch_table.property("delay_spin")
                if delay_spin:
                    delay_spin.setValue(self.config.get("start_delay", 3))
                
                self.config["current_config"] = config_name
                self.save_config()
                self.log(f"切换到配置: {config_name}")
            except Exception as e:
                QMessageBox.warning(self, "切换失败", f"加载配置失败:\n{str(e)}")

    def _save_current_config(self):
        """保存当前配置"""
        from PyQt5.QtWidgets import QInputDialog
        
        # 获取当前配置名
        current_config = self.config.get("current_config", "默认配置")
        
        # 弹出输入框
        config_name, ok = QInputDialog.getText(
            self, "保存配置", 
            "配置名称:",
            text=current_config
        )
        
        if not ok or not config_name:
            return
        
        # 构建配置
        config_data = {
            "ros_setup": self.ros_setup_edit.text().strip(),
            "ws_setup": self.ws_setup_edit.text().strip(),
            "start_delay": self.launch_table.property("delay_spin").value(),
            "launch_files": [t.to_dict() for _, t, _ in self._rows_of(self.launch_table)],
            "py_files": [t.to_dict() for _, t, _ in self._rows_of(self.py_table)],
        }
        
        # 保存配置文件
        config_dir = os.path.join(BASE_DIR, "configs")
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, f"{config_name}.json")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.config["current_config"] = config_name
            self.save_config()
            
            # 刷新配置列表
            self._load_config_list()
            
            # 设置当前配置
            index = self.config_combo.findText(config_name)
            if index >= 0:
                self.config_combo.setCurrentIndex(index)
            
            self.log(f"配置已保存: {config_name}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存配置失败:\n{str(e)}")

    def _batch_select_all(self):
        """全选所有任务"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            table.selectAll()

    def _batch_deselect_all(self):
        """取消全选"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            table.clearSelection()

    def _batch_set_restart(self, enabled):
        """批量设置崩溃重启"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            for r, task, item in self._rows_of(table):
                task.auto_restart = enabled
                restart_item = table.item(r, COL_RESTART)
                if restart_item:
                    restart_item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
        
        self.save_config()
        self.log(f"批量{'启用' if enabled else '禁用'}崩溃重启")

    def _batch_set_autostart(self, enabled):
        """批量设置自启动"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            for r, task, item in self._rows_of(table):
                task.auto_start = enabled
                autostart_item = table.item(r, COL_AUTOSTART)
                if autostart_item:
                    autostart_item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
        
        self.save_config()
        self.log(f"批量{'启用' if enabled else '禁用'}自启动")
