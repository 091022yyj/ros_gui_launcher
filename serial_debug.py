#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口调试器模块
- 扫描并选择串口设备
- 波特率选择
- 接收串口数据并实时显示
- 支持发送数据（可选发送新行）
"""
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QPlainTextEdit, QLineEdit,
                             QCheckBox, QMessageBox)
from ros_widget_base import ROSWidget

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class SerialDebugWidget(ROSWidget):
    """串口调试器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port = None
        self._init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._read_serial)
        self.timer.start(50)

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 串口选择行
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("串口:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        port_row.addWidget(self.port_combo, 1)
        scan_btn = QPushButton("扫描端口")
        scan_btn.clicked.connect(self.scan_ports)
        port_row.addWidget(scan_btn)
        layout.addLayout(port_row)

        # 波特率行
        baud_row = QHBoxLayout()
        baud_row.addWidget(QLabel("波特率:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "57600", "38400"])
        self.baud_combo.setCurrentText("115200")
        baud_row.addWidget(self.baud_combo, 1)
        self.toggle_btn = QPushButton("打开串口")
        self.toggle_btn.clicked.connect(self.toggle_serial)
        baud_row.addWidget(self.toggle_btn)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_received)
        baud_row.addWidget(clear_btn)
        layout.addLayout(baud_row)

        # 接收区
        layout.addWidget(QLabel("接收区:"))
        self.receive_view = QPlainTextEdit()
        self.receive_view.setReadOnly(True)
        self.receive_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1f29;
                color: #f8f8f2;
                border: 1px solid #44475a;
                border-radius: 6px;
                padding: 4px;
                font-family: "DejaVu Sans Mono", monospace;
            }
        """)
        layout.addWidget(self.receive_view, 1)

        # 发送区
        layout.addWidget(QLabel("发送区:"))
        send_row = QHBoxLayout()
        self.send_edit = QLineEdit()
        self.send_edit.returnPressed.connect(self._send_data)
        self.send_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f29;
                color: #f8f8f2;
                border: 1px solid #44475a;
                border-radius: 6px;
                padding: 6px 8px;
                font-family: "DejaVu Sans Mono", monospace;
            }
        """)
        send_row.addWidget(self.send_edit, 1)
        self.newline_check = QCheckBox("发送新行")
        self.newline_check.setChecked(True)
        send_row.addWidget(self.newline_check)
        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self._send_data)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #50fa7b;
                color: #1e1f29;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #69ff94; }
        """)
        send_row.addWidget(send_btn)
        layout.addLayout(send_row)

        # 状态提示
        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: #6272a4;")
        layout.addWidget(self.status_label)

    def scan_ports(self):
        """扫描串口设备"""
        ports = []
        try:
            for name in sorted(os.listdir("/dev")):
                if name.startswith(("ttyUSB", "ttyACM", "ttyS")):
                    ports.append("/dev/" + name)
        except OSError as e:
            QMessageBox.warning(self, "扫描端口", f"扫描失败: {e}")
            return
        if ports:
            self.port_combo.clear()
            self.port_combo.addItems(ports)
            self.status_label.setText(f"发现 {len(ports)} 个串口")
        else:
            self.status_label.setText("未发现串口设备")

    def toggle_serial(self):
        """打开/关闭串口"""
        if self.serial_port and self.serial_port.is_open:
            self._close_serial()
        else:
            self._open_serial()

    def _open_serial(self):
        """打开串口"""
        if not HAS_SERIAL:
            QMessageBox.warning(self, "串口调试", "未安装pyserial: pip install pyserial")
            return
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "串口调试", "请选择或输入串口")
            return
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=int(self.baud_combo.currentText()),
                timeout=0,
            )
            self.serial_port.flushInput()
        except Exception as e:
            self.serial_port = None
            QMessageBox.warning(self, "串口调试", f"打开失败: {e}")
            return
        self.toggle_btn.setText("关闭串口")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5555;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ff6e6e; }
        """)
        self.status_label.setText(f"已连接 {port} @ {self.baud_combo.currentText()}")

    def _close_serial(self):
        """关闭串口"""
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None
        self.toggle_btn.setText("打开串口")
        self.toggle_btn.setStyleSheet("")
        self.status_label.setText("已断开")

    def _read_serial(self):
        """定时读取串口数据"""
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            waiting = self.serial_port.in_waiting
            if waiting > 0:
                data = self.serial_port.read(waiting)
                self.receive_view.appendPlainText(data.decode(errors="replace"))
        except Exception as e:
            self.status_label.setText(f"读取错误: {e}")

    def _send_data(self):
        """发送数据"""
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self, "串口调试", "请先打开串口")
            return
        text = self.send_edit.text()
        if not text:
            return
        if self.newline_check.isChecked():
            text += "\r\n"
        try:
            self.serial_port.write(text.encode("utf-8", errors="replace"))
        except Exception as e:
            QMessageBox.warning(self, "串口调试", f"发送失败: {e}")

    def _clear_received(self):
        """清空接收区"""
        self.receive_view.clear()

    def closeEvent(self, event):
        """关闭时释放串口"""
        self._close_serial()
        super().closeEvent(event)
