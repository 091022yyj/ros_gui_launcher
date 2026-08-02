#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遥控面板模块
- 键盘方向键/WASD控制小车(cmd_vel)
- 速度仪表盘显示
- 紧急停止
"""
import os
import subprocess
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QPen, QPainter, QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QSlider, QMessageBox)


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


class RobotControlWidget(QWidget):
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

    def _run_cmd(self, cmd, timeout=3):
        full = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        try:
            subprocess.run(["bash", "-c", full], capture_output=True,
                           text=True, timeout=timeout)
        except Exception:
            pass

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

        topic_btn = QPushButton("设置话题")
        topic_btn.clicked.connect(self._set_topic)
        btn_row.addWidget(topic_btn)
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

    def _set_topic(self):
        from PyQt5.QtWidgets import QInputDialog
        topic, ok = QInputDialog.getText(self, "设置控制话题", "cmd_vel话题:",
                                         text=self.cmd_vel_topic)
        if ok and topic:
            self.cmd_vel_topic = topic

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
        # 发布3次零速度确保停止
        for _ in range(3):
            self._run_cmd(
                f"rostopic pub -1 {self.cmd_vel_topic} geometry_msgs/Twist "
                f"'{{linear: {{x: 0, y: 0, z: 0}}, angular: {{x: 0, y: 0, z: 0}}}}'"
            )
        self.log_if_any("已紧急停止")

    def log_if_any(self, text):
        pass
