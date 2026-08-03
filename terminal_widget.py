#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置终端组件
- 支持运行ROS命令
- 支持预置命令快捷按钮
- 支持命令历史
"""
import os
import signal
from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QPlainTextEdit, QComboBox, QGroupBox, QSplitter,
)
from ros_widget_base import ROSWidget


class TerminalWidget(ROSWidget):
    """内置终端组件"""

    def __init__(self, parent=None, ros_setup="", ws_setup=""):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.process = None
        self.command_history = []
        self.history_index = -1

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部工具栏
        toolbar = QHBoxLayout()

        # ROS环境设置
        toolbar.addWidget(QLabel("ROS环境:"))
        self.ros_setup_label = QLabel(self.ros_setup or "未设置")
        self.ros_setup_label.setStyleSheet("color: #8ab4f8;")
        toolbar.addWidget(self.ros_setup_label)

        toolbar.addStretch()

        # 清空按钮
        clear_btn = QPushButton("清空终端")
        clear_btn.clicked.connect(self.clear_terminal)
        toolbar.addWidget(clear_btn)

        # 终止进程按钮
        self.kill_btn = QPushButton("终止进程")
        self.kill_btn.setEnabled(False)
        self.kill_btn.clicked.connect(self.kill_process)
        toolbar.addWidget(self.kill_btn)

        layout.addLayout(toolbar)

        # 终端输出
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(10000)
        self.output.setFont(QFont("DejaVu Sans Mono", 11))
        self.output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1a2e;
                color: #00ff00;
                border: 1px solid #3a4048;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.output)

        # 命令输入
        input_layout = QHBoxLayout()

        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        input_layout.addWidget(self.prompt_label)

        self.command_input = QLineEdit()
        self.command_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a2e;
                color: #00ff00;
                border: 1px solid #3a4048;
                border-radius: 6px;
                padding: 6px 8px;
                font-family: "DejaVu Sans Mono", monospace;
            }
        """)
        self.command_input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.command_input)

        exec_btn = QPushButton("执行")
        exec_btn.clicked.connect(self.execute_command)
        input_layout.addWidget(exec_btn)

        layout.addLayout(input_layout)

        # 预置命令按钮
        preset_group = QGroupBox("常用ROS命令")
        preset_layout = QHBoxLayout(preset_group)

        preset_commands = [
            ("rostopic list", "查看话题"),
            ("rosnode list", "查看节点"),
            ("rostopic info", "话题信息"),
            ("rosnode info", "节点信息"),
            ("rospack list", "查看包"),
            ("rosservice list", "查看服务"),
            ("rosparam list", "查看参数"),
            ("rosmsg list", "查看消息类型"),
        ]

        for cmd, tooltip in preset_commands:
            btn = QPushButton(cmd)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda _, c=cmd: self.run_preset_command(c))
            preset_layout.addWidget(btn)

        layout.addWidget(preset_group)


    def execute_command(self):
        """执行命令"""
        command = self.command_input.text().strip()
        if not command:
            return

        # 添加到历史记录
        self.command_history.append(command)
        self.history_index = len(self.command_history)

        # 清空输入框
        self.command_input.clear()

        # 显示命令
        self.output.appendPlainText(f"$ {command}")

        # 构建完整命令
        full_cmd = command
        if self.ros_setup and os.path.exists(self.ros_setup):
            full_cmd = f"source '{self.ros_setup}' && "
            if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
                full_cmd += f"source '{os.path.expanduser(self.ws_setup)}' && "
            full_cmd += command

        # 启动进程
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.finished.connect(self._on_finished)

        self.process.start("bash", ["-c", full_cmd])
        self.kill_btn.setEnabled(True)

    def run_preset_command(self, command):
        """运行预置命令"""
        self.command_input.setText(command)
        self.execute_command()

    def _on_output(self):
        """输出回调"""
        if self.process:
            output = self.process.readAllStandardOutput().data().decode(errors="replace")
            self.output.appendPlainText(output.rstrip())

    def _on_finished(self, exit_code, exit_status):
        """进程结束回调"""
        self.kill_btn.setEnabled(False)
        if exit_code != 0:
            self.output.appendPlainText(f"[进程退出，退出码: {exit_code}]")

    def kill_process(self):
        """终止进程"""
        if self.process and self.process.state() == QProcess.Running:
            pid = self.process.processId()
            if pid:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except OSError:
                    pass
            self.process.terminate()
            self.output.appendPlainText("[进程已终止]")

    def clear_terminal(self):
        """清空终端"""
        self.output.clear()

    def keyPressEvent(self, event):
        """按键事件"""
        if event.key() == Qt.Key_Up:
            # 上一条历史命令
            if self.history_index > 0:
                self.history_index -= 1
                self.command_input.setText(self.command_history[self.history_index])
        elif event.key() == Qt.Key_Down:
            # 下一条历史命令
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_input.setText(self.command_history[self.history_index])
            else:
                self.history_index = len(self.command_history)
                self.command_input.clear()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """关闭事件"""
        self.kill_process()
        super().closeEvent(event)
