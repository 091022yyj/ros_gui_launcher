#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遥控面板模块
- 键盘方向键/WASD控制小车(cmd_vel)
- 速度仪表盘显示
- 紧急停止
"""
import os
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QPen, QPainter, QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QSlider, QMessageBox,
                             QInputDialog)
from ros_widget_base import ROSWidget
from env_cache import run_cmd


class SpeedGauge(QWidget):
    """速度仪表盘"""

    def __init__(self, parent=None, title="速度"):
        super().__init__(parent)
        self.title = title
        self.value = 0.0
        self.max_value = 2.0
        self.setMinimumSize(220, 160)

    def set_value(self, v):
        self.value = max(-self.max_value, min(self.max_value, v))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        cx, cy = w // 2, int(h * 0.55)
        r = min(w, h) // 2 - 15

        # 背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e1f29"))
        painter.drawRoundedRect(0, 0, w, h, 10, 10)

        # 表盘弧
        pen = QPen(QColor("#44475a"), 8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 0, 180 * 16)

        # 数值弧
        ratio = self.value / self.max_value  # -1..1
        angle = ratio * 180
        color = QColor("#50fa7b") if abs(self.value) < self.max_value * 0.6 else QColor("#ff5555")
        pen2 = QPen(color, 8)
        pen2.setCapStyle(Qt.RoundCap)
        painter.setPen(pen2)
        start_angle = 180 * 16
        span = -int(angle * 16)
        painter.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), start_angle, span)

        # 标题
        painter.setPen(QColor("#6272a4"))
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(0, 8, w, 20), Qt.AlignCenter, self.title)

        # 数值
        painter.setPen(QColor("#f8f8f2"))
        font2 = QFont()
        font2.setPointSize(22)
        font2.setBold(True)
        painter.setFont(font2)
        painter.drawText(QRectF(0, cy - r + 30, w, 40), Qt.AlignCenter,
                         f"{self.value:.2f}")

        # 单位
        painter.setPen(QColor("#6272a4"))
        font3 = QFont()
        font3.setPointSize(9)
        painter.setFont(font3)
        painter.drawText(QRectF(0, cy + 20, w, 20), Qt.AlignCenter, "m/s")
        painter.end()


class RobotControlWidget(ROSWidget):
    """遥控面板"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.cmd_vel_topic = "/cmd_vel"
        self.linear = 0.0
        self.angular = 0.0
        self._build_source_cmd()
        self._init_ui()
        self.setFocusPolicy(Qt.StrongFocus)


    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 仪表盘
        gauge_group = QGroupBox("速度仪表盘")
        gauge_layout = QHBoxLayout(gauge_group)
        self.linear_gauge = SpeedGauge(title="线速度")
        self.angular_gauge = SpeedGauge(title="角速度 rad/s")
        self.angular_gauge.max_value = 3.0
        gauge_layout.addWidget(self.linear_gauge)
        gauge_layout.addWidget(self.angular_gauge)
        layout.addWidget(gauge_group)

        # 控制说明
        info = QLabel("方向键/WASD控制 | 空格=停止 | 方向键上/下=前后 左/右=转向\n"
                      "持续按住控制,松开回零")
        info.setStyleSheet("color: #6272a4; padding: 4px;")
        layout.addWidget(info)

        # 速度滑杆
        speed_group = QGroupBox("最大速度设置")
        speed_layout = QVBoxLayout(speed_group)
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("线速度上限:"))
        self.linear_slider = QSlider(Qt.Horizontal)
        self.linear_slider.setRange(5, 100)
        self.linear_slider.setValue(30)
        self.linear_slider.valueChanged.connect(
            lambda v: self.linear_limit_label.setText(f"{v/100:.2f} m/s"))
        speed_row.addWidget(self.linear_slider, 1)
        self.linear_limit_label = QLabel("0.30 m/s")
        speed_row.addWidget(self.linear_limit_label)
        speed_layout.addLayout(speed_row)

        ang_row = QHBoxLayout()
        ang_row.addWidget(QLabel("角速度上限:"))
        self.angular_slider = QSlider(Qt.Horizontal)
        self.angular_slider.setRange(10, 300)
        self.angular_slider.setValue(100)
        self.angular_slider.valueChanged.connect(
            lambda v: self.angular_limit_label.setText(f"{v/100:.2f} rad/s"))
        ang_row.addWidget(self.angular_slider, 1)
        self.angular_limit_label = QLabel("1.00 rad/s")
        ang_row.addWidget(self.angular_limit_label)
        speed_layout.addLayout(ang_row)
        layout.addWidget(speed_group)

        # 紧急停止
        btn_row = QHBoxLayout()
        self.stop_btn = QPushButton("🛑 紧急停止")
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #ff5555; color: white;
                font-size: 16px; font-weight: bold; padding: 12px; border-radius: 8px; }
            QPushButton:hover { background-color: #ff7e7e; }
        """)
        self.stop_btn.clicked.connect(self.emergency_stop)
        btn_row.addWidget(self.stop_btn)

        detect_btn = QPushButton("自动检测")
        detect_btn.clicked.connect(self._auto_detect_topic)
        btn_row.addWidget(detect_btn)

        topic_btn = QPushButton("设置话题")
        topic_btn.clicked.connect(self._set_topic)
        btn_row.addWidget(topic_btn)

        self.topic_label = QLabel(f"当前话题: {self.cmd_vel_topic}")
        self.topic_label.setStyleSheet("color: #6272a4; padding: 4px;")
        btn_row.addWidget(self.topic_label)
        layout.addLayout(btn_row)

        layout.addStretch()

        # 定时器持续发布速度(仅速度非零时发布,减少进程开销)
        self.publish_timer = QTimer()
        self.publish_timer.timeout.connect(self._publish_velocity)
        self.publish_timer.start(200)  # 5Hz

    def pause_timers(self):
        self.publish_timer.stop()

    def resume_timers(self):
        self.publish_timer.start(200)

    def _detect_topics(self):
        """自动检测cmd相关话题,返回话题列表"""
        out, _, _ = self._run_cmd(
            "rostopic list 2>/dev/null | grep -E 'cmd_vel|cmd_vel_mux|teleop' | head -10",
            timeout=5)
        if not out:
            return []
        return [t.strip() for t in out.splitlines() if t.strip()]

    def _pick_topic(self, topics):
        """弹出下拉选择框(可手动输入),供选择话题"""
        items = topics if topics else [self.cmd_vel_topic or "/cmd_vel"]
        try:
            current = items.index(self.cmd_vel_topic)
        except ValueError:
            current = 0
        topic, ok = QInputDialog.getItem(
            self, "设置控制话题", "选择或输入cmd_vel话题:", items, current, True)
        if ok and topic and topic.strip():
            self.cmd_vel_topic = topic.strip()
            self.topic_label.setText(f"当前话题: {self.cmd_vel_topic}")

    def _auto_detect_topic(self):
        """自动检测话题: 找到/cmd_vel直接使用,否则列出候选供选择"""
        topics = self._detect_topics()
        if not topics:
            QMessageBox.information(self, "自动检测", "未检测到cmd相关话题\n"
                                     "请确认ROS节点已启动,或手动设置话题")
            return
        if "/cmd_vel" in topics:
            self.cmd_vel_topic = "/cmd_vel"
            self.topic_label.setText(f"当前话题: {self.cmd_vel_topic}")
            QMessageBox.information(self, "自动检测", "已自动使用话题: /cmd_vel")
        else:
            self._pick_topic(topics)

    def _set_topic(self):
        topics = self._detect_topics() or [self.cmd_vel_topic]
        self._pick_topic(topics)

    def keyPressEvent(self, event):
        key = event.key()
        lin_max = self.linear_slider.value() / 100.0
        ang_max = self.angular_slider.value() / 100.0
        if key == Qt.Key_Up or key == Qt.Key_W:
            self.linear = lin_max
        elif key == Qt.Key_Down or key == Qt.Key_S:
            self.linear = -lin_max
        elif key == Qt.Key_Left or key == Qt.Key_A:
            self.angular = ang_max
        elif key == Qt.Key_Right or key == Qt.Key_D:
            self.angular = -ang_max
        elif key == Qt.Key_Space:
            self.emergency_stop()
        self._update_gauges()

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_W, Qt.Key_S):
            self.linear = 0.0
        elif key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_A, Qt.Key_D):
            self.angular = 0.0
        self._update_gauges()

    def _update_gauges(self):
        self.linear_gauge.set_value(self.linear)
        self.angular_gauge.set_value(self.angular)

    def _publish_velocity(self):
        # 仅在速度非零时发布,降低进程开销
        if self.linear == 0 and self.angular == 0:
            return
        self._run_cmd(
            f"rostopic pub -1 {self.cmd_vel_topic} geometry_msgs/Twist "
            f"'{{linear: {{x: {self.linear}, y: 0, z: 0}}, "
            f"angular: {{x: 0, y: 0, z: {self.angular}}}}}'"
        )

    def emergency_stop(self):
        self.linear = 0.0
        self.angular = 0.0
        self._update_gauges()
        # 3次零速发布合并为一条bash命令,只启动1次进程,确保零速立即发出
        pub = (f"rostopic pub -1 {self.cmd_vel_topic} geometry_msgs/Twist "
               f"'{{linear: {{x: 0, y: 0, z: 0}}, angular: {{x: 0, y: 0, z: 0}}}}'")
        self._run_cmd("; ".join([pub] * 3), timeout=5)
        self.log_if_any("已紧急停止")

    def log_if_any(self, text):
        pass
