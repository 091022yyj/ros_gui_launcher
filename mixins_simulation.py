#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mixins_simulation.py - SimulationMixin
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


class SimulationMixin:
    """MainWindow功能mixin"""

    def _add_schedule(self):
        """添加定时任务"""
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "添加定时任务", "任务名称:")
        if not ok or not name:
            return

        # 选择任务类型
        task_type, ok = QInputDialog.getItem(self, "选择任务类型", "类型:",
                                             ["launch", "py"], 0, False)
        if not ok:
            return

        # 选择任务路径
        if task_type == "launch":
            path, _ = QFileDialog.getOpenFileName(self, "选择launch文件",
                                                  os.path.expanduser("~"),
                                                  "Launch文件 (*.launch)")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择Python文件",
                                                  os.path.expanduser("~"),
                                                  "Python文件 (*.py)")

        if not path:
            return

        # 选择调度类型
        schedule_type, ok = QInputDialog.getItem(self, "选择调度类型", "类型:",
                                                 ["once", "repeat"], 0, False)
        if not ok:
            return

        interval = None
        if schedule_type == "repeat":
            interval, ok = QInputDialog.getInt(self, "设置间隔", "间隔秒数:", 3600, 60, 86400)
            if not ok:
                return

        self.task_scheduler.add_schedule(
            name, task_type, path, schedule_type, interval=interval
        )
        self._refresh_schedules()
        self.log(f"添加定时任务: {name}")

    def _refresh_schedules(self):
        """刷新调度列表"""
        self.schedule_tree.clear()
        schedules = self.task_scheduler.get_schedule_list()

        for schedule in schedules:
            item = QTreeWidgetItem([
                schedule["name"],
                schedule["task_type"],
                schedule["task_path"],
                "启用" if schedule["enabled"] else "禁用",
                schedule.get("next_run", "未计划")
            ])
            self.schedule_tree.addTopLevelItem(item)

    def _pause_simulation(self):
        """暂停仿真(异步)"""
        self._status_label.setText("暂停仿真中...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("仿真已暂停")
            else:
                QMessageBox.warning(self, "错误", f"暂停仿真失败:\n{result['error']}")
        self._run_async(lambda: self.sim_controller.pause_simulation(), on_done)

    def _unpause_simulation(self):
        """继续仿真(异步)"""
        self._status_label.setText("继续仿真中...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("仿真已继续")
            else:
                QMessageBox.warning(self, "错误", f"继续仿真失败:\n{result['error']}")
        self._run_async(lambda: self.sim_controller.unpause_simulation(), on_done)

    def _reset_simulation(self):
        """重置仿真(异步)"""
        self._status_label.setText("重置仿真中...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("仿真已重置")
            else:
                QMessageBox.warning(self, "错误", f"重置仿真失败:\n{result['error']}")
        self._run_async(lambda: self.sim_controller.reset_simulation(), on_done)

    def _start_gazebo(self):
        """启动Gazebo空世界(异步)"""
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self._status_label.setText("启动Gazebo中...")
        self.start_gazebo_btn.setEnabled(False)

        def on_done(result):
            self.start_gazebo_btn.setEnabled(True)
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("Gazebo已启动")
                self.gazebo_status_label.setText("Gazebo: 运行中")
                self.gazebo_status_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
                self._refresh_gazebo_models()
            else:
                QMessageBox.warning(self, "错误", f"启动Gazebo失败:\n{result['error']}")

        self._run_async(lambda: self.sim_controller.start_gazebo(), on_done)

    def _stop_gazebo(self):
        """停止Gazebo(异步)"""
        self._status_label.setText("停止Gazebo中...")
        def on_done(result):
            self._status_label.setText("就绪")
            self.gazebo_status_label.setText("Gazebo: 未运行")
            self.gazebo_status_label.setStyleSheet("color: #6272a4;")
            self.model_list.clear()
            self.log("Gazebo已停止")
        self._run_async(lambda: self.sim_controller.stop_gazebo(), on_done)

    def _refresh_gazebo_status(self):
        """刷新Gazebo状态(异步)"""
        def on_done(result):
            running = result.get("running", False)
            if running:
                self.gazebo_status_label.setText("Gazebo: 运行中")
                self.gazebo_status_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
                self._refresh_gazebo_models()
            else:
                self.gazebo_status_label.setText("Gazebo: 未运行")
                self.gazebo_status_label.setStyleSheet("color: #6272a4;")

        self._run_async(
            lambda: {"running": self.sim_controller.is_gazebo_running()},
            on_done
        )

    def _start_scene(self):
        """启动仿真场景(异步)"""
        text = self.scene_combo.currentText()
        if not text:
            QMessageBox.information(self, "提示", "请选择仿真场景")
            return
        # 格式: "pkg/file.launch"
        try:
            pkg, file = text.split("/", 1)
        except ValueError:
            QMessageBox.warning(self, "错误", "场景格式错误")
            return

        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self._status_label.setText(f"启动场景 {text} ...")

        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"场景已启动: {text}")
                self.gazebo_status_label.setText("Gazebo: 场景运行中")
                self.gazebo_status_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
                self._refresh_gazebo_models()
            else:
                QMessageBox.warning(self, "错误", f"启动场景失败:\n{result['error']}")

        self._run_async(
            lambda: self.sim_controller.start_simulation_scene(pkg, file),
            on_done
        )

    def _load_urdf_model(self):
        """加载URDF模型(异步)"""
        from PyQt5.QtWidgets import QInputDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择URDF文件",
                                              os.path.expanduser("~"),
                                              "URDF文件 (*.urdf)")
        if not path:
            return
        model_name, ok = QInputDialog.getText(self, "模型名称", "模型名称:", text="robot")
        if not ok or not model_name:
            return
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self._status_label.setText(f"加载URDF模型 {model_name} ...")
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"URDF模型已加载: {model_name}")
                self._refresh_gazebo_models()
            else:
                QMessageBox.warning(self, "错误", f"加载URDF失败:\n{result['error']}")
        self._run_async(
            lambda: self.sim_controller.spawn_urdf_model(path, model_name),
            on_done
        )

    def _load_sdf_model(self):
        """加载SDF模型(异步)"""
        from PyQt5.QtWidgets import QInputDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择SDF文件",
                                              os.path.expanduser("~"),
                                              "SDF文件 (*.sdf)")
        if not path:
            return
        model_name, ok = QInputDialog.getText(self, "模型名称", "模型名称:", text="robot")
        if not ok or not model_name:
            return
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self._status_label.setText(f"加载SDF模型 {model_name} ...")
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"SDF模型已加载: {model_name}")
                self._refresh_gazebo_models()
            else:
                QMessageBox.warning(self, "错误", f"加载SDF失败:\n{result['error']}")
        self._run_async(
            lambda: self.sim_controller.spawn_sdf_model(path, model_name),
            on_done
        )

    def _refresh_gazebo_models(self):
        """刷新模型列表(异步)"""
        self.model_list.clear()
        self.model_list.addItem("加载中...")
        def on_done(result):
            self.model_list.clear()
            models = result.get("models", [])
            if not models:
                self.model_list.addItem("无模型(或Gazebo未运行)")
            else:
                for m in models:
                    self.model_list.addItem(f"🤖 {m}")
        self._run_async(lambda: self.sim_controller.get_gazebo_models(), on_done)

    def _delete_model(self):
        """删除模型(异步)"""
        item = self.model_list.currentItem()
        if item and not item.text().startswith("🤖"):
            QMessageBox.information(self, "提示", "请先在模型列表中选择模型")
            return
        model_name = item.text().replace("🤖 ", "") if item else ""
        if not model_name or model_name == "无模型(或Gazebo未运行)":
            model_name, ok = QInputDialog.getText(self, "删除模型", "模型名称:")
            if not ok or not model_name:
                return
        self._status_label.setText(f"删除模型 {model_name} ...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"模型已删除: {model_name}")
                self._refresh_gazebo_models()
            else:
                QMessageBox.warning(self, "错误", f"删除模型失败:\n{result['error']}")
        self._run_async(lambda: self.sim_controller.delete_model(model_name), on_done)

    def _analyze_all_logs(self):
        """分析所有日志"""
        analysis = self.log_analyzer.analyze_all_logs()

        if "error" in analysis:
            QMessageBox.warning(self, "错误", f"分析日志失败:\n{analysis['error']}")
            return

        report = self.log_analyzer.generate_report(analysis)
        self.analysis_result.setPlainText(report)
        self.log(f"日志分析完成: {analysis['total_errors']}个错误, {analysis['total_warnings']}个警告")

    def _search_errors(self):
        """搜索错误"""
        from PyQt5.QtWidgets import QInputDialog

        keyword, ok = QInputDialog.getText(self, "搜索错误", "关键词:")
        if not ok:
            return

        results = self.log_analyzer.search_errors(keyword=keyword)

        report = f"搜索结果: {len(results)}条匹配\n\n"
        for r in results[:50]:  # 最多显示50条
            report += f"[{r['file']}] 行{r['line']}: {r['content'][:100]}\n"

        self.analysis_result.setPlainText(report)

    def _export_report(self):
        """导出分析报告"""
        path, _ = QFileDialog.getSaveFileName(self, "导出报告",
                                              os.path.expanduser("~/log_report.txt"),
                                              "文本文件 (*.txt)")
        if not path:
            return

        analysis = self.log_analyzer.analyze_all_logs()
        report = self.log_analyzer.generate_report(analysis, path)
        self.log(f"报告已导出: {path}")
