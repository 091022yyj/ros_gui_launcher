#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器面板模块
- 电池电压/电量监控
- 激光雷达状态
- IMU状态
- 定时刷新
"""
import os
import subprocess
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QProgressBar, QPushButton, QGridLayout,
                             QPlainTextEdit)
from ros_widget_base import ROSWidget


class SensorPanelWidget(ROSWidget):
    """传感器面板"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()
        self._init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start(5000)  # 5秒刷新

    def pause_timers(self):
        self.refresh_timer.stop()

    def resume_timers(self):
        self.refresh_timer.start(5000)


    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 电池状态
        battery_group = QGroupBox("🔋 电池")
        battery_layout = QVBoxLayout(battery_group)
        batt_row = QHBoxLayout()
        batt_row.addWidget(QLabel("电量:"))
        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(0)
        batt_row.addWidget(self.battery_bar, 1)
        self.battery_label = QLabel("--%")
        batt_row.addWidget(self.battery_label)
        battery_layout.addLayout(batt_row)
        batt_voltage_row = QHBoxLayout()
        batt_voltage_row.addWidget(QLabel("电压:"))
        self.voltage_label = QLabel("-- V")
        self.voltage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #8be9fd;")
        batt_voltage_row.addWidget(self.voltage_label)
        batt_voltage_row.addStretch()
        battery_layout.addLayout(batt_voltage_row)
        layout.addWidget(battery_group)

        # 传感器状态
        sensor_group = QGroupBox("📡 传感器状态")
        sensor_grid = QGridLayout(sensor_group)

        self.sensor_labels = {}
        sensors = [
            ("laser", "激光雷达"),
            ("imu", "IMU"),
            ("odom", "里程计"),
            ("camera", "摄像头"),
            ("sonar", "超声波"),
            ("gps", "GPS"),
        ]
        for i, (key, name) in enumerate(sensors):
            row, col = divmod(i, 2)
            box = QGroupBox(name)
            box_layout = QVBoxLayout(box)
            label = QLabel("--")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 14px; padding: 8px;")
            box_layout.addWidget(label)
            sensor_grid.addWidget(box, row, col)
            self.sensor_labels[key] = (label, box)
        layout.addWidget(sensor_group)

        # 原始数据
        data_group = QGroupBox("📊 传感器原始数据")
        data_layout = QVBoxLayout(data_group)
        self.data_view = QPlainTextEdit()
        self.data_view.setReadOnly(True)
        self.data_view.setMaximumHeight(200)
        data_layout.addWidget(self.data_view)
        layout.addWidget(data_group)

        # 刷新按钮
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 立即刷新")
        refresh_btn.clicked.connect(self.refresh_all)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def refresh_all(self):
        """刷新所有传感器状态(后台线程执行,不阻塞界面)"""
        def worker():
            stdout, _, code = self._run_cmd("rostopic list 2>/dev/null", timeout=4)
            topics = set()
            if code == 0 and stdout:
                topics = set(t.strip() for t in stdout.split("\n") if t.strip())
            return topics

        def on_done(topics):
            if not topics:
                # ROS master未运行
                for key, label in self.sensor_labels.items():
                    label[0].setText("✗ 未检测到")
                    label[0].setStyleSheet("font-size: 13px; padding: 8px; color: #ff5555;")
                self.battery_label.setText("ROS未连接")
                self.battery_bar.setValue(0)
                self.voltage_label.setText("-- V")
                self.data_view.setPlainText("无法连接ROS主节点\n\n请确认roscore运行中")
                return
            self._check_sensors(topics)
            self._refresh_battery(topics)

        self._run_bg(worker, on_done)

    def _refresh_battery(self, topics):
        """根据话题列表检查电池(纯内存判断,不跑命令)"""
        # 常见电池话题
        battery_topics = [
            "/battery_level", "/battery", "/battery_status",
            "/sensor/battery", "/power/battery",
        ]
        found = None
        for topic in battery_topics:
            if topic in topics:
                found = topic
                break
        if not found:
            # 模糊匹配
            for t in topics:
                if "battery" in t.lower():
                    found = t
                    break
        if not found:
            self.battery_label.setText("未检测到电池话题")
            self.battery_bar.setValue(0)
            self.voltage_label.setText("-- V")
            return
        # 只对找到的话题取一次数据
        stdout, _, code = self._run_cmd(f"rostopic echo -n1 {found} 2>/dev/null | head -10",
                                        timeout=3)
        if code == 0 and stdout:
            self._parse_battery(stdout, found)

    def _parse_battery(self, data, topic):
        import re
        lines = data.split("\n")
        for line in lines:
            line = line.strip()
            m = re.search(r"(percentage|percent|level|charge|battery_level)\s*:\s*([\d.]+)", line)
            if m:
                pct = float(m.group(2))
                if pct > 1.0:
                    pct = pct / 100.0  # 可能是0-100
                pct = max(0, min(100, pct * 100))
                self.battery_bar.setValue(int(pct))
                self.battery_label.setText(f"{pct:.0f}%")
                # 颜色
                if pct > 30:
                    self.battery_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
                elif pct > 15:
                    self.battery_label.setStyleSheet("color: #f1fa8c; font-weight: bold;")
                else:
                    self.battery_label.setStyleSheet("color: #ff5555; font-weight: bold;")
            m = re.search(r"(voltage|volts)\s*:\s*([\d.]+)", line)
            if m:
                self.voltage_label.setText(f"{float(m.group(2)):.2f} V")

    def _check_sensors(self, topics):
        """根据话题列表检查传感器(纯内存判断,不跑命令)"""
        sensor_topics = {
            "laser": ["/scan", "/laser/scan", "/scan_raw"],
            "imu": ["/imu", "/imu/data", "/imu_data"],
            "odom": ["/odom", "/odometry/filtered"],
            "camera": ["/camera/image_raw", "/image_raw", "/usb_cam/image_raw"],
            "sonar": ["/sonar", "/sonars"],
            "gps": ["/gps", "/fix", "/gps/fix"],
        }
        info_lines = []
        for key, label in self.sensor_labels.items():
            text = "✗ 未检测到"
            color = "#ff5555"
            found_topic = None
            candidates = sensor_topics.get(key, [])
            for topic in candidates:
                if topic in topics:
                    found_topic = topic
                    break
            if not found_topic:
                # 模糊匹配
                for t in topics:
                    if key in t.lower() or (key == "camera" and "image" in t.lower()):
                        found_topic = t
                        break
            if found_topic:
                text = f"✓ 正常\n{found_topic}"
                color = "#50fa7b"
                info_lines.append(f"[{key}] {found_topic}")
            label[0].setText(text)
            label[0].setStyleSheet(f"font-size: 13px; padding: 8px; color: {color};")
            box_style = f"""
                QGroupBox {{ background-color: #262b33; border: 1px solid #3a4149;
                    border-radius: 8px; }}
                QGroupBox::title {{ color: #6272a4; }}
            """
            label[1].setStyleSheet(box_style)

        if info_lines:
            self.data_view.setPlainText("\n".join(info_lines))
        else:
            self.data_view.setPlainText("未检测到活跃传感器话题\n\n"
                                        "请确认ROS主节点运行中且传感器驱动已启动")
