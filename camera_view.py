#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头画面模块
- 自动检测有发布者的图像话题(Gazebo/真实相机通用)
- 显示ROS摄像头话题图像
- 支持切换话题、截图保存
"""
import os
import subprocess
import tempfile
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QComboBox, QFileDialog,
                             QMessageBox)
from ros_widget_base import ROSWidget


class CameraViewWidget(ROSWidget):
    """摄像头画面"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.current_topic = ""
        self._build_source_cmd()
        self._init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._grab_frame)
        self.refresh_timer.start(800)
        # 不自动检测,避免启动卡顿;页面可见时(resume_timers)才检测

    def pause_timers(self):
        self.refresh_timer.stop()

    def resume_timers(self):
        if not self.preview_btn.isChecked():
            self.refresh_timer.start(800)
        # 首次进入页面时自动检测话题
        if not self.current_topic:
            QTimer.singleShot(300, self._auto_detect)


    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("图像话题:"))
        self.topic_combo = QComboBox()
        self.topic_combo.setEditable(True)
        self.topic_combo.setPlaceholderText("选择或输入话题...")
        toolbar.addWidget(self.topic_combo, 1)
        detect_btn = QPushButton("🔍 自动检测")
        detect_btn.clicked.connect(self._auto_detect)
        toolbar.addWidget(detect_btn)
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
        self.image_label.setText("未连接摄像头\n\n点击[自动检测]查找图像话题")
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

    def _auto_detect(self):
        """自动检测有发布者的图像话题(异步,不阻塞界面)"""
        self.status_label.setText("检测中...")
        self.image_label.setText("正在检测图像话题...")
        # 列出所有图像相关话题, 检查发布者(后台执行)
        cmd = (
            "for t in $(rostopic list 2>/dev/null | grep -iE 'image|camera|video|usb_cam' "
            "| grep -vE '/camera_info|parameter|_updates|theora|compressedDepth|depth'); do "
            "pub=$(rostopic info $t 2>/dev/null | grep -A1 'Publishers:' | grep -c '\\*'); "
            "[ \"$pub\" -gt 0 ] && echo $t; done"
        )

        def worker():
            return self._run_cmd(cmd, timeout=12)

        def on_done(result):
            stdout, _, code = result
            if code == 0 and stdout:
                topics = [t.strip() for t in stdout.split("\n") if t.strip()]
                if topics:
                    self.topic_combo.clear()
                    self.topic_combo.addItems(topics)
                    # 优先选择常见话题
                    preferred = ["/camera/image_raw", "/kinect2/hd/image_color_rect",
                                 "/usb_cam/image_raw", "/cv_camera/image_raw"]
                    sel = topics[0]
                    for p in preferred:
                        if p in topics:
                            sel = p
                            break
                    self.topic_combo.setCurrentText(sel)
                    self.current_topic = sel
                    self.status_label.setText(f"检测到 {len(topics)} 个话题, 已连接: {sel}")
                    self._grab_frame()
                    return
            self.status_label.setText("未检测到图像话题(请确认Gazebo/相机驱动已启动)")
            self.image_label.setText("未检测到活跃图像话题\n\n请确认:\n1. Gazebo或相机驱动已启动\n2. 有节点在发布图像话题")

        self._run_bg(worker, on_done)

    def _connect_topic(self):
        self.current_topic = self.topic_combo.currentText().strip()
        if self.current_topic:
            self.status_label.setText(f"连接: {self.current_topic}")
            self._grab_frame()
        else:
            QMessageBox.information(self, "提示", "请输入话题名称")

    def _toggle_preview(self):
        if self.preview_btn.isChecked():
            self.preview_btn.setText("▶ 继续预览")
            self.refresh_timer.stop()
        else:
            self.preview_btn.setText("⏸ 暂停预览")
            self.refresh_timer.start()

    def _grab_frame(self):
        """抓取一帧图像"""
        if not self.current_topic:
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp_name = tmp.name
        tmp.close()
        stdout, stderr, code = self._run_cmd(
            f"rm -f '{tmp_name}'; "
            f"rosrun image_view extract_images _sec_per_frame:=100 "
            f"_filename_format:='{tmp_name}' image:={self.current_topic} "
            f"__name:=gui_cam_grab 2>/dev/null & "
            f"sleep 2; pkill -f gui_cam_grab 2>/dev/null; "
            f"ls '{tmp_name}' 2>/dev/null",
            timeout=8
        )
        if os.path.exists(tmp_name):
            pixmap = QPixmap(tmp_name)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.image_label.size(),
                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.status_label.setText(f"{self.current_topic} | {pixmap.width()}x{pixmap.height()}")
            else:
                self.status_label.setText(f"{self.current_topic} | 图像无效")
            os.remove(tmp_name)
        else:
            self.status_label.setText(f"{self.current_topic} | 无数据(检查发布者)")

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
