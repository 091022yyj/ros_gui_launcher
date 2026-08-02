#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报警系统模块
- 监控ROS节点/话题状态
- 低电量报警
- 桌面通知+声音
"""
import os
import subprocess
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QCheckBox, QMessageBox)


class AlarmSystemWidget(QWidget):
    """报警系统"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.monitored = []  # [(type, name)]
        self.alarm_states = {}
        self.notifications_enabled = True
        self._build_source_cmd()
        self._init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_all)
        self.timer.start(10000)

    def pause_timers(self):
        self.timer.stop()

    def resume_timers(self):
        self.timer.start(10000)

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

    def _run_cmd(self, cmd, timeout=8):
        full = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        try:
            result = subprocess.run(["bash", "-c", full], capture_output=True,
                                    text=True, timeout=timeout)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except Exception:
            return "", "超时", 1

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 状态概览
        overview = QHBoxLayout()
        self.master_label = QLabel("ROS主节点: --")
        self.master_label.setStyleSheet("font-size: 14px;")
        overview.addWidget(self.master_label)
        overview.addStretch()
        self.alarm_count_label = QLabel("报警: 0")
        self.alarm_count_label.setStyleSheet("font-size: 14px; color: #50fa7b;")
        overview.addWidget(self.alarm_count_label)
        layout.addLayout(overview)

        # 监控配置
        cfg_group = QGroupBox("监控配置")
        cfg_layout = QHBoxLayout(cfg_group)
        cfg_layout.addWidget(QLabel("节点名:"))
        self.node_edit = QLabel("(自动监控launch/py任务)")
        self.node_edit.setStyleSheet("color: #6272a4;")
        cfg_layout.addWidget(self.node_edit, 1)
        layout.addWidget(cfg_group)

        # 报警记录
        alarm_group = QGroupBox("⚠ 报警记录")
        alarm_layout = QVBoxLayout(alarm_group)
        self.alarm_table = QTableWidget(0, 3)
        self.alarm_table.setHorizontalHeaderLabels(["时间", "项目", "状态"])
        self.alarm_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.alarm_table.verticalHeader().setVisible(False)
        alarm_layout.addWidget(self.alarm_table)
        layout.addWidget(alarm_group, 1)

        # 控制
        ctrl_row = QHBoxLayout()
        self.notify_check = QCheckBox("桌面通知")
        self.notify_check.setChecked(True)
        self.notify_check.toggled.connect(lambda on: setattr(self, 'notifications_enabled', on))
        ctrl_row.addWidget(self.notify_check)
        check_btn = QPushButton("🔄 立即检查")
        check_btn.clicked.connect(self.check_all)
        ctrl_row.addWidget(check_btn)
        clear_btn = QPushButton("🗑 清空记录")
        clear_btn.clicked.connect(self._clear_alarms)
        ctrl_row.addWidget(clear_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

    def set_monitored_nodes(self, node_paths):
        """从主窗口获取launch/py任务路径"""
        self.monitored = []
        for p in node_paths:
            self.monitored.append(("node", os.path.basename(p)))
        if self.monitored:
            self.node_edit.setText(", ".join(n for _, n in self.monitored))

    def check_all(self):
        """检查所有监控项(只跑2次命令,降低开销)"""
        if not self.monitored:
            self.master_label.setText("ROS主节点: 未配置监控")
            return

        alarms = []
        # 一次命令获取节点列表(同时判断主节点)
        nodes_stdout, _, _ = self._run_cmd("rosnode list 2>/dev/null", timeout=5)
        master_ok = bool(nodes_stdout.strip())
        self.master_label.setText(f"ROS主节点: {'✓ 运行中' if master_ok else '✗ 未运行'}")
        self.master_label.setStyleSheet(
            "font-size: 14px; color: #50fa7b;" if master_ok else
            "font-size: 14px; color: #ff5555;")
        if not master_ok:
            alarms.append(("ROS主节点", "未运行"))

        # 检查节点
        nodes_ok = [n for n in nodes_stdout.split("\n") if n.strip()] if nodes_stdout else []
        for _, node in self.monitored:
            found = any(node in n for n in nodes_ok)
            if not found:
                alarms.append((node, "进程异常/节点消失"))
                if self.notifications_enabled:
                    self._notify(f"节点异常: {node}")

        # 检查低电量(仅当主节点正常时)
        if master_ok:
            battery = self._check_battery()
            if battery is not None and battery < 20:
                alarms.append(("电池", f"电量低: {battery:.0f}%"))
                if self.notifications_enabled:
                    self._notify(f"电池电量低: {battery:.0f}%")

        # 更新报警记录
        self.alarm_count_label.setText(f"报警: {len(alarms)}")
        if alarms:
            self.alarm_count_label.setStyleSheet("font-size: 14px; color: #ff5555;")
        else:
            self.alarm_count_label.setStyleSheet("font-size: 14px; color: #50fa7b;")

        self.alarm_table.insertRow(0)
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        for i, (name, status) in enumerate(alarms[:1]):  # 只显示最新一条
            self.alarm_table.setItem(0, 0, QTableWidgetItem(ts))
            self.alarm_table.setItem(0, 1, QTableWidgetItem(name))
            self.alarm_table.setItem(0, 2, QTableWidgetItem(status))
        if not alarms:
            self.alarm_table.setItem(0, 0, QTableWidgetItem(ts))
            self.alarm_table.setItem(0, 1, QTableWidgetItem("正常"))
            self.alarm_table.setItem(0, 2, QTableWidgetItem("✓"))
        while self.alarm_table.rowCount() > 100:
            self.alarm_table.removeRow(self.alarm_table.rowCount() - 1)

    def _check_battery(self):
        stdout, _, code = self._run_cmd(
            "rostopic echo -n1 /battery_level 2>/dev/null | grep -E 'percentage|percent|level' | head -1",
            timeout=5)
        if code == 0 and stdout:
            try:
                v = float(stdout.split(":")[-1].strip())
                if v > 1.0:
                    v = v / 100.0
                return v * 100
            except ValueError:
                pass
        return None

    def _notify(self, message):
        try:
            subprocess.Popen(["notify-send", "-u", "critical",
                              "ROS启动器报警", message])
        except Exception:
            pass
        # 声音
        try:
            subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _clear_alarms(self):
        self.alarm_table.setRowCount(0)
