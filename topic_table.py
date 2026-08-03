#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
话题数据表模块
- 实时显示任意话题的数值
- 支持数字、字符串话题
- 定时刷新
"""
import os
import subprocess
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QComboBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox,
                             QCheckBox)


class TopicTableWidget(QWidget):
    """话题数据表"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.monitored_topics = []
        self._build_source_cmd()
        self._init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start(2000)

    def pause_timers(self):
        self.refresh_timer.stop()

    def resume_timers(self):
        if self.auto_refresh_check.isChecked():
            self.refresh_timer.start(2000)

    def _build_source_cmd(self):
        parts = []
        if self.ros_setup and os.path.exists(self.ros_setup):
            parts.append(f"source '{self.ros_setup}'")
        if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
            parts.append(f"source '{os.path.expanduser(self.ws_setup)}'")
        self.source_cmd = " && ".join(parts) if parts else ""

    def set_ros_env(self, ros_setup, ws_setup):
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()


    def _run_bg(self, fn, on_done=None):
        """后台线程执行,完成后主线程回调(线程安全)"""
        from async_helper import run_async
        run_async(fn, on_done)

    def _run_cmd(self, cmd, timeout=5):
        full = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        try:
            result = subprocess.run(["bash", "-c", full], capture_output=True,
                                    text=True, timeout=timeout)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except Exception:
            return "", "超时", 1

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("话题:"))
        self.topic_combo = QComboBox()
        self.topic_combo.setEditable(True)
        self.topic_combo.setPlaceholderText("输入或选择话题...")
        toolbar.addWidget(self.topic_combo, 1)
        scan_btn = QPushButton("扫描")
        scan_btn.clicked.connect(self._scan_topics)
        toolbar.addWidget(scan_btn)
        add_btn = QPushButton("➕ 添加监控")
        add_btn.clicked.connect(self._add_monitor)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        # 数据表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["话题", "字段", "值"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # 控制
        ctrl_row = QHBoxLayout()
        self.auto_refresh_check = QCheckBox("自动刷新")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.toggled.connect(
            lambda on: self.refresh_timer.start() if on else self.refresh_timer.stop())
        ctrl_row.addWidget(self.auto_refresh_check)
        refresh_btn = QPushButton("🔄 立即刷新")
        refresh_btn.clicked.connect(self._refresh_data)
        ctrl_row.addWidget(refresh_btn)
        clear_btn = QPushButton("🗑 清空")
        clear_btn.clicked.connect(self._clear_monitors)
        ctrl_row.addWidget(clear_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

    def _scan_topics(self):
        stdout, _, code = self._run_cmd("rostopic list 2>/dev/null | head -50", timeout=8)
        if code == 0 and stdout:
            topics = [t for t in stdout.split("\n") if t.strip()]
            self.topic_combo.clear()
            self.topic_combo.addItems(topics)

    def _add_monitor(self):
        topic = self.topic_combo.currentText().strip()
        if not topic:
            QMessageBox.information(self, "提示", "请输入话题名称")
            return
        if topic not in self.monitored_topics:
            if len(self.monitored_topics) >= 5:
                QMessageBox.information(self, "提示", "最多同时监控5个话题(避免卡顿)")
                return
            self.monitored_topics.append(topic)
        self._refresh_data()

    def _clear_monitors(self):
        self.monitored_topics = []
        self.table.setRowCount(0)

    def _refresh_data(self):
        """刷新话题数据"""
        rows = []
        for topic in self.monitored_topics:
            stdout, _, code = self._run_cmd(
                f"rostopic echo -n1 {topic} 2>/dev/null | head -25", timeout=5)
            if code == 0 and stdout:
                parsed = self._parse_message(stdout)
                if parsed:
                    for field, value in parsed[:8]:
                        rows.append((topic, field, value))
                else:
                    rows.append((topic, "data", stdout[:60]))
            else:
                rows.append((topic, "-", "无数据"))

        self.table.setRowCount(0)
        for i, (topic, field, value) in enumerate(rows):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(topic))
            self.table.setItem(i, 1, QTableWidgetItem(field))
            self.table.setItem(i, 2, QTableWidgetItem(value))

    def _parse_message(self, data):
        """解析rostopic echo输出"""
        result = []
        for line in data.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("---"):
                field, _, value = line.partition(":")
                field = field.strip()
                value = value.strip()
                if field and value and value not in ("", "---"):
                    result.append((field, value))
        return result
