#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头画面模块
- 显示ROS摄像头话题图像
- 支持切换话题
- 截图保存
"""
import os
import subprocess
import tempfile
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QComboBox, QFileDialog,
                             QMessageBox)


class CameraViewWidget(QWidget):
    """摄像头画面"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.current_topic = "/camera/image_raw"
        self._build_source_cmd()
        self._init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._grab_frame)
        self.refresh_timer.start(600)  # 降低抓帧频率

    def pause_timers(self):
        self.refresh_timer.stop()

    def resume_timers(self):
        if not self.preview_btn.isChecked():
            self.refresh_timer.start(600)

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

    def _run_cmd(self, cmd, timeout=10):
        full = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        try:
            result = subprocess.run(["bash", "-c", full], capture_output=True,
                                    text=True, timeout=timeout)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except Exception as e:
            return "", str(e), 1

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        self.topic_combo = QComboBox()
        self.topic_combo.setEditable(True)
        self.topic_combo.setCurrentText(self.current_topic)
        toolbar.addWidget(QLabel("图像话题:"))
        toolbar.addWidget(self.topic_combo, 1)
        scan_btn = QPushButton("扫描话题")
        scan_btn.clicked.connect(self._scan_topics)
        toolbar.addWidget(scan_btn)
        connect_btn = QPushButton("连接")
        connect_btn.clicked.connect(self._connect_topic)
        toolbar.addWidget(connect_btn)
        layout.addLayout(toolbar)

        # 画面
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("""
            background-color: #1e1f29; border: 1px solid #44475a; border-radius: 8px;
            color: #6272a4; font-size: 14px;
        """)
        self.image_label.setText("未连接摄像头\n\n请设置图像话题并点击连接")
        layout.addWidget(self.image_label, 1)

        # 底部按钮
        btn_row = QHBoxLayout()
        self.preview_btn = QPushButton("⏸ 暂停预览")
        self.preview_btn.setCheckable(True)
        self.preview_btn.clicked.connect(self._toggle_preview)
        btn_row.addWidget(self.preview_btn)
        save_btn = QPushButton("📷 截图保存")
        save_btn.clicked.connect(self._save_screenshot)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: #6272a4;")
        btn_row.addWidget(self.status_label)
        layout.addLayout(btn_row)

    def _scan_topics(self):
        """扫描图像话题"""
        stdout, stderr, code = self._run_cmd(
            "rostopic list 2>/dev/null | grep -iE 'image|camera|video' | head -20",
            timeout=8)
        if code == 0 and stdout:
            topics = [t for t in stdout.split("\n") if t.strip()]
            self.topic_combo.clear()
            self.topic_combo.addItems(topics)
            self.status_label.setText(f"发现 {len(topics)} 个图像话题")
        else:
            self.status_label.setText("未发现图像话题")

    def _connect_topic(self):
        self.current_topic = self.topic_combo.currentText().strip()
        self.status_label.setText(f"连接: {self.current_topic}")

    def _toggle_preview(self):
        if self.preview_btn.isChecked():
            self.preview_btn.setText("▶ 继续预览")
            self.refresh_timer.stop()
        else:
            self.preview_btn.setText("⏸ 暂停预览")
            self.refresh_timer.start()

    def _grab_frame(self):
        """抓取一帧图像"""
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.close()
        stdout, stderr, code = self._run_cmd(
            f"rosrun image_view extract_images _sec_per_frame:=100 _filename_format:='{tmp.name}' "
            f"image:={self.current_topic} __name:=gui_camera_grab 2>/dev/null & "
            f"sleep 1.5; pkill -f gui_camera_grab; ls {tmp.name} 2>/dev/null",
            timeout=8
        )
        # 检查文件是否存在
        if os.path.exists(tmp.name):
            pixmap = QPixmap(tmp.name)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.image_label.size(),
                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.status_label.setText(f"{self.current_topic} | {pixmap.width()}x{pixmap.height()}")
            os.remove(tmp.name)

    def _save_screenshot(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存截图",
                                              os.path.expanduser("~/camera.png"),
                                              "PNG图片 (*.png)")
        if path:
            if self.image_label.pixmap():
                self.image_label.pixmap().save(path)
                QMessageBox.information(self, "截图", f"已保存: {path}")
            else:
                QMessageBox.warning(self, "截图", "当前没有图像")
