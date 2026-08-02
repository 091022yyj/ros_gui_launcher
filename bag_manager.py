#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rosbag管理模块
- 录制/停止录制(带话题选择)
- 播放bag(带速率)
- bag列表管理
"""
import os
import subprocess
import signal
from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QListWidget, QLineEdit,
                             QDoubleSpinBox, QFileDialog, QMessageBox,
                             QInputDialog)


class BagManagerWidget(QWidget):
    """rosbag管理"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.bag_dir = os.path.join(os.path.expanduser("~"), "bags")
        self.record_process = None
        self._build_source_cmd()
        os.makedirs(self.bag_dir, exist_ok=True)
        self._init_ui()
        self._refresh_bag_list()

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

        # 录制控制
        rec_group = QGroupBox("🎙 录制")
        rec_layout = QHBoxLayout(rec_group)
        self.record_btn = QPushButton("⏺ 开始录制")
        self.record_btn.setStyleSheet("""
            QPushButton { background-color: #ff5555; color: white; font-size: 14px;
                font-weight: bold; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background-color: #ff7e7e; }
        """)
        self.record_btn.clicked.connect(self._toggle_record)
        rec_layout.addWidget(self.record_btn)
        rec_layout.addWidget(QLabel("话题(逗号分隔,空=全部):"))
        self.topics_edit = QLineEdit()
        self.topics_edit.setPlaceholderText("如: /cmd_vel,/odom (留空录制全部)")
        rec_layout.addWidget(self.topics_edit, 1)
        layout.addWidget(rec_group)

        # 播放控制
        play_group = QGroupBox("▶ 播放")
        play_layout = QHBoxLayout(play_group)
        play_layout.addWidget(QLabel("速率:"))
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.1, 5.0)
        self.rate_spin.setValue(1.0)
        self.rate_spin.setSingleStep(0.1)
        play_layout.addWidget(self.rate_spin)
        play_btn = QPushButton("▶ 播放选中")
        play_btn.clicked.connect(self._play_selected)
        play_layout.addWidget(play_btn)
        play_once_btn = QPushButton("⏸ 暂停播放")
        play_once_btn.clicked.connect(self._pause_play)
        play_layout.addWidget(play_once_btn)
        layout.addWidget(play_group)

        # bag列表
        list_group = QGroupBox("📁 Bag文件")
        list_layout = QVBoxLayout(list_group)
        self.bag_list = QListWidget()
        self.bag_list.itemDoubleClicked.connect(lambda item: self._play_bag(item.text()))
        list_layout.addWidget(self.bag_list)
        list_btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._refresh_bag_list)
        list_btn_row.addWidget(refresh_btn)
        info_btn = QPushButton("ℹ 信息")
        info_btn.clicked.connect(self._bag_info)
        list_btn_row.addWidget(info_btn)
        delete_btn = QPushButton("🗑 删除")
        delete_btn.clicked.connect(self._delete_bag)
        list_btn_row.addWidget(delete_btn)
        open_btn = QPushButton("📂 打开目录")
        open_btn.clicked.connect(self._open_dir)
        list_btn_row.addWidget(open_btn)
        list_btn_row.addStretch()
        list_layout.addLayout(list_btn_row)
        layout.addWidget(list_group, 1)

    # ---------- 录制 ----------

    def _toggle_record(self):
        if self.record_process:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bag_name = f"record_{timestamp}.bag"
        bag_path = os.path.join(self.bag_dir, bag_name)
        topics = self.topics_edit.text().strip()
        cmd = f"rosbag record -O '{bag_path}'"
        if topics:
            cmd += " " + topics
        else:
            cmd += " -a"
        full = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        try:
            self.record_process = subprocess.Popen(
                ["bash", "-c", full], preexec_fn=os.setsid)
            self.record_btn.setText("⏹ 停止录制")
            self.record_btn.setStyleSheet("""
                QPushButton { background-color: #50fa7b; color: #282a36;
                    font-size: 14px; font-weight: bold; padding: 10px 20px; border-radius: 8px; }
                QPushButton:hover { background-color: #7dffa1; }
            """)
        except Exception as e:
            QMessageBox.warning(self, "录制失败", str(e))

    def _stop_record(self):
        if self.record_process:
            try:
                pgid = os.getpgid(self.record_process.pid)
                os.killpg(pgid, signal.SIGINT)
                try:
                    self.record_process.wait(timeout=5)
                except Exception:
                    os.killpg(pgid, signal.SIGKILL)
            except Exception:
                pass
            self.record_process = None
        self.record_btn.setText("⏺ 开始录制")
        self.record_btn.setStyleSheet("""
            QPushButton { background-color: #ff5555; color: white; font-size: 14px;
                font-weight: bold; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background-color: #ff7e7e; }
        """)
        self._refresh_bag_list()

    # ---------- 播放 ----------

    def _play_selected(self):
        item = self.bag_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一个bag文件")
            return
        self._play_bag(item.text())

    def _play_bag(self, bag_name):
        bag_path = os.path.join(self.bag_dir, bag_name)
        if not os.path.exists(bag_path):
            QMessageBox.warning(self, "错误", "文件不存在")
            return
        rate = self.rate_spin.value()
        self._run_cmd(f"nohup rosbag play '{bag_path}' -r {rate} > /tmp/bag_play.log 2>&1 &",
                      timeout=3)

    def _pause_play(self):
        self._run_cmd("pkill -STOP -f 'rosbag play'", timeout=3)

    # ---------- 列表管理 ----------

    def _refresh_bag_list(self):
        self.bag_list.clear()
        if not os.path.exists(self.bag_dir):
            return
        for f in sorted(os.listdir(self.bag_dir), reverse=True):
            if f.endswith(".bag"):
                path = os.path.join(self.bag_dir, f)
                size_mb = os.path.getsize(path) / 1024 / 1024
                self.bag_list.addItem(f"{f}  ({size_mb:.1f}MB)")

    def _bag_info(self):
        item = self.bag_list.currentItem()
        if not item:
            return
        bag_name = item.text().split("  (")[0]
        bag_path = os.path.join(self.bag_dir, bag_name)
        stdout, stderr, code = self._run_cmd(f"rosbag info '{bag_path}'", timeout=10)
        if code == 0 and stdout:
            QMessageBox.information(self, "Bag信息", stdout[:2000])
        else:
            QMessageBox.warning(self, "错误", stderr or "无法读取")

    def _delete_bag(self):
        item = self.bag_list.currentItem()
        if not item:
            return
        bag_name = item.text().split("  (")[0]
        reply = QMessageBox.question(self, "删除", f"删除 {bag_name}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(os.path.join(self.bag_dir, bag_name))
                self._refresh_bag_list()
            except OSError as e:
                QMessageBox.warning(self, "错误", str(e))

    def _open_dir(self):
        os.system(f'xdg-open "{self.bag_dir}" 2>/dev/null &')
