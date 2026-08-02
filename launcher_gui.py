#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS 一键启动器
- 自定义添加 launch 文件和 py 文件
- 一键启动 / 停止(停止会杀掉整个进程组,包括 gazebo 等子孙进程)
- 顺序延时启动、每任务自定义启动参数、崩溃自动重启、随软件自启动
- 配置自动保存(原子写入),日志同时写入 logs/ 目录
"""
import datetime
import json
import os
import signal
import sys
import shlex
import platform
import traceback

from security import SecurityManager
from config_manager import ConfigManager
from monitor import ProcessMonitor
from updater import Updater
from log_manager import LogManager
from ros_translator import ROSTranslator
from scene_manager import SceneManager
from terminal_widget import TerminalWidget
from ros_monitor import ROSMonitor
from task_scheduler import TaskScheduler
from simulation_controller import SimulationController
from log_analyzer import LogAnalyzer
from tf_monitor import TFMonitor
from data_visualizer import DataVisualizer
from chart_widget import TrendChartWidget
from multi_machine import MultiMachineController
from plugin_manager import PluginManager

# ---- 可选功能模块(文件缺失时自动跳过,不影响主程序) ----
try:
    from robot_control import RobotControlWidget
except Exception as e:
    print(f"加载robot_control失败: {e}")
    RobotControlWidget = None

try:
    from navigation_panel import NavigationWidget
except Exception as e:
    print(f"加载navigation_panel失败: {e}")
    NavigationWidget = None

try:
    from sensor_panel import SensorPanelWidget
except Exception as e:
    print(f"加载sensor_panel失败: {e}")
    SensorPanelWidget = None

try:
    from camera_view import CameraViewWidget
except Exception as e:
    print(f"加载camera_view失败: {e}")
    CameraViewWidget = None

try:
    from topic_table import TopicTableWidget
except Exception as e:
    print(f"加载topic_table失败: {e}")
    TopicTableWidget = None

try:
    from bag_manager import BagManagerWidget
except Exception as e:
    print(f"加载bag_manager失败: {e}")
    BagManagerWidget = None

try:
    from alarm_system import AlarmSystemWidget
except Exception as e:
    print(f"加载alarm_system失败: {e}")
    AlarmSystemWidget = None

try:
    from serial_debug import SerialDebugWidget
except Exception as e:
    print(f"加载serial_debug失败: {e}")
    SerialDebugWidget = None

try:
    from web_remote import WebRemoteWidget
except Exception as e:
    print(f"加载web_remote失败: {e}")
    WebRemoteWidget = None

from functools import lru_cache
from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QHeaderView, QSpinBox, QTabWidget, QProgressBar,
    QListWidget, QListWidgetItem, QDockWidget, QSplitter, QTreeWidget,
    QTreeWidgetItem, QHeaderView as QTreeHeaderView, QComboBox, QShortcut,
    QStackedWidget,
)

# PyInstaller 打包后 __file__ 指向临时解压目录,
# 配置和日志要放在可执行文件旁边,否则每次运行都会丢失
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
VERSION = "3.5.0"

DEFAULT_CONFIG = {
    "ros_setup": "/opt/ros/noetic/setup.bash",
    "ws_setup": "",  # 例如 ~/catkin_ws/devel/setup.bash
    "start_delay": 3,  # 顺序启动时每个任务之间的延时(秒)
    "launch_files": [],
    "py_files": [],
    "history": [],  # 历史记录
    "current_scene": None,  # 当前场景
    "scenes": {},  # 场景配置
    "translation_enabled": True,  # 启用翻译
    "hotkeys": {
        "start_all": "F5",
        "stop_all": "F6",
        "start_selected": "F7",
        "stop_selected": "F8",
    },
}

MAX_RESTARTS = 3  # 崩溃自动重启的最大次数

# 表格列
COL_STATUS, COL_PATH, COL_ARGS, COL_RESTART, COL_AUTOSTART, COL_OPS = range(6)

APP_QSS = """/* ============================================================
   ROS GUI启动器 - Dracula Dark 主题
   设计参考: dracula/dracula-theme (★25k, GitHub最受欢迎主题)
   配色: 深紫底#282a36 + 青色#8be9fd + 绿#50fa7b + 红#ff5555
   ============================================================ */
* {
    font-family: "Segoe UI", "Noto Sans CJK SC", "WenQuanYi Micro Hei", sans-serif;
    font-size: 13px;
    outline: none;
}
QMainWindow, QWidget {
    background-color: #282a36;
    color: #f8f8f2;
    font-size: 13px;
}
/* ---- 卡片 ---- */
QGroupBox {
    background-color: #2f3241;
    border: 1px solid #44475a;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 12px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 10px;
    color: #8be9fd;
    background-color: #2f3241;
    border-radius: 6px;
}
/* ---- 按钮 ---- */
QPushButton {
    background-color: #44475a;
    border: 1px solid #4d5068;
    border-radius: 6px;
    padding: 7px 16px;
    color: #f8f8f2;
}
QPushButton:hover {
    background-color: #55597a;
    border-color: #8be9fd;
}
QPushButton:pressed { background-color: #383a4b; }
QPushButton:disabled {
    background-color: #343746;
    color: #6b6f88;
    border-color: #3f4252;
}
/* 启动/停止按钮 */
QPushButton#btnStart {
    background-color: #50fa7b;
    border: none;
    border-radius: 6px;
    padding: 5px 16px;
    color: #282a36;
    font-weight: bold;
}
QPushButton#btnStart:hover { background-color: #7dffa1; }
QPushButton#btnStart:pressed { background-color: #3ecf63; }
QPushButton#btnStop {
    background-color: #ff5555;
    border: none;
    border-radius: 6px;
    padding: 5px 16px;
    color: #282a36;
    font-weight: bold;
}
QPushButton#btnStop:hover { background-color: #ff7e7e; }
QPushButton#btnStop:pressed { background-color: #e64545; }
/* 全局启动/停止 */
QPushButton#btnGlobalStart {
    background-color: #50fa7b;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: bold;
    padding: 12px 32px;
    color: #282a36;
}
QPushButton#btnGlobalStart:hover { background-color: #7dffa1; }
QPushButton#btnGlobalStart:pressed { background-color: #3ecf63; }
QPushButton#btnGlobalStop {
    background-color: #ff5555;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: bold;
    padding: 12px 32px;
    color: #282a36;
}
QPushButton#btnGlobalStop:hover { background-color: #ff7e7e; }
QPushButton#btnGlobalStop:pressed { background-color: #e64545; }
/* ---- 输入框 ---- */
QLineEdit {
    background-color: #21222c;
    border: 1px solid #44475a;
    border-radius: 6px;
    padding: 7px 10px;
    color: #f8f8f2;
    selection-background-color: #bd93f9;
    selection-color: #282a36;
}
QLineEdit:hover { border-color: #6272a4; }
QLineEdit:focus {
    border-color: #8be9fd;
    background-color: #262738;
}
QSpinBox {
    background-color: #21222c;
    border: 1px solid #44475a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #f8f8f2;
}
QSpinBox:focus { border-color: #8be9fd; }
/* ---- 表格 ---- */
QTableWidget {
    background-color: #232530;
    alternate-background-color: #282a38;
    gridline-color: #383b4d;
    border: 1px solid #44475a;
    border-radius: 8px;
    selection-background-color: #bd93f9;
    selection-color: #282a36;
}
QTableWidget::item {
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2c2f3e;
}
QTableWidget::item:selected {
    background-color: #bd93f9;
    color: #282a36;
}
QHeaderView::section {
    background-color: #343746;
    color: #8be9fd;
    border: none;
    border-right: 1px solid #44475a;
    border-bottom: 1px solid #44475a;
    padding: 8px;
    font-weight: bold;
}
QTableCornerButton::section { background-color: #343746; }
/* ---- 文本框 ---- */
QPlainTextEdit {
    background-color: #1e1f29;
    border: 1px solid #44475a;
    border-radius: 8px;
    color: #50fa7b;
    font-family: "Cascadia Code", "DejaVu Sans Mono", "Noto Sans Mono CJK SC", monospace;
    font-size: 12px;
    padding: 6px;
    selection-background-color: #bd93f9;
    selection-color: #282a36;
}
QPlainTextEdit:focus { border-color: #8be9fd; }
/* ---- 滚动条 ---- */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #4d5068;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover { background: #6272a4; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #4d5068;
    min-width: 30px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover { background: #6272a4; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
/* ---- 提示 ---- */
QToolTip {
    background-color: #44475a;
    color: #f8f8f2;
    border: 1px solid #6272a4;
    border-radius: 4px;
    padding: 6px 10px;
}
/* ---- 列表 ---- */
QListWidget {
    background-color: #1e1f29;
    border: 1px solid #44475a;
    border-radius: 8px;
    color: #f8f8f2;
}
QListWidget::item { padding: 7px 10px; border-radius: 5px; }
QListWidget::item:selected {
    background-color: #bd93f9;
    color: #282a36;
}
QListWidget::item:hover { background-color: #343746; }
/* ---- 分割器 ---- */
QSplitter::handle {
    background-color: #343746;
}
QSplitter::handle:hover { background-color: #8be9fd; }
QSplitter::handle:vertical { height: 4px; }
QSplitter::handle:horizontal { width: 4px; }
/* ---- 标签页 ---- */
QTabWidget::pane {
    border: 1px solid #44475a;
    border-radius: 8px;
    top: -1px;
    background-color: #282a36;
}
QTabBar::tab {
    background-color: #343746;
    color: #6272a4;
    border: 1px solid #44475a;
    border-bottom: none;
    padding: 9px 20px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:hover { background-color: #44475a; color: #f8f8f2; }
QTabBar::tab:selected {
    background-color: #282a36;
    color: #8be9fd;
    font-weight: bold;
    border-bottom: 2px solid #8be9fd;
}
/* ---- 下拉框 ---- */
QComboBox {
    background-color: #21222c;
    border: 1px solid #44475a;
    border-radius: 6px;
    padding: 7px 12px;
    color: #f8f8f2;
}
QComboBox:hover { border-color: #6272a4; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background-color: #21222c;
    border: 1px solid #44475a;
    selection-background-color: #bd93f9;
    selection-color: #282a36;
    color: #f8f8f2;
    outline: none;
    padding: 4px;
}
/* ---- 进度条 ---- */
QProgressBar {
    background-color: #21222c;
    border: 1px solid #44475a;
    border-radius: 5px;
    text-align: center;
    color: #6272a4;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #8be9fd;
    border-radius: 4px;
}
/* ---- 树形控件 ---- */
QTreeWidget {
    background-color: #232530;
    alternate-background-color: #282a38;
    border: 1px solid #44475a;
    border-radius: 8px;
    color: #f8f8f2;
}
QTreeWidget::item { padding: 6px; border-radius: 4px; }
QTreeWidget::item:selected { background-color: #bd93f9; color: #282a36; }
QTreeWidget::item:hover { background-color: #343746; }
QTreeWidget::branch { background: transparent; }
/* ---- 状态栏 ---- */
QStatusBar {
    background-color: #21222c;
    color: #6272a4;
    border-top: 1px solid #44475a;
}
QStatusBar::item { border: none; }
QStatusBar QLabel { color: #6272a4; padding: 0 8px; }
/* ---- 菜单 ---- */
QMenuBar {
    background-color: #282a36;
    color: #f8f8f2;
}
QMenuBar::item:selected { background-color: #44475a; border-radius: 4px; }
QMenu {
    background-color: #2f3241;
    color: #f8f8f2;
    border: 1px solid #44475a;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #bd93f9; color: #282a36; }
/* ---- 复选框 ---- */
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #6272a4;
    background-color: #21222c;
}
QCheckBox::indicator:hover { border-color: #8be9fd; }
QCheckBox::indicator:checked {
    background-color: #8be9fd;
    border-color: #8be9fd;
}
/* ---- Dock ---- */
QDockWidget { color: #f8f8f2; font-weight: bold; }
QDockWidget::title {
    background-color: #2f3241;
    padding: 6px;
    border: 1px solid #44475a;
}
/* ---- 左侧导航栏 ---- */
QListWidget#navList {
    background-color: #21222c;
    border: none;
    border-right: 1px solid #44475a;
    border-radius: 0;
    padding: 6px 0;
    outline: none;
}
QListWidget#navList::item {
    padding: 10px 16px;
    border-radius: 8px;
    margin: 2px 6px;
    color: #a0a2b8;
    font-size: 13px;
}
QListWidget#navList::item:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #f8f8f2;
}
QListWidget#navList::item:selected {
    background-color: #44475a;
    color: #8be9fd;
    font-weight: bold;
    border-left: 3px solid #8be9fd;
}
"""


def normalize_task(entry):
    """配置项兼容:字符串(旧格式)或字典"""
    if isinstance(entry, str):
        return {"path": entry, "args": "", "auto_restart": False, "auto_start": False}
    task = {"path": "", "args": "", "auto_restart": False, "auto_start": False}
    task.update(entry)
    return task


class ProcessRow:
    """管理一行任务:路径 + 参数 + QProcess 进程"""

    def __init__(self, path, kind, args="", auto_restart=False, auto_start=False):
        self.path = path
        self.kind = kind  # "launch" 或 "py"
        self.args = args
        self.auto_restart = auto_restart
        self.auto_start = auto_start
        self.process = None
        self.stop_requested = False
        self.restart_count = 0

    def _py_interpreter(self):
        """读取 py 文件首行的 shebang,优先使用其中指定的解释器(如 conda 环境的 python)"""
        try:
            with open(self.path, "rb") as f:
                first = f.readline().decode("utf-8", errors="replace").strip()
            if first.startswith("#!"):
                parts = first[2:].strip().split()
                # 处理 #!/usr/bin/env python3 形式
                if parts and parts[0].endswith("env") and len(parts) > 1:
                    return parts[1]
                if parts:
                    return parts[0]
        except OSError:
            pass
        return "python3"

    def build_command(self, ros_setup, ws_setup):
        parts = []
        if ros_setup and os.path.exists(ros_setup):
            parts.append("source '%s'" % ros_setup)
        if ws_setup and os.path.exists(os.path.expanduser(ws_setup)):
            parts.append("source '%s'" % os.path.expanduser(ws_setup))
        if self.kind == "launch":
            parts.append("roslaunch '%s'" % self.path)
        else:
            parts.append("'%s' '%s'" % (self._py_interpreter(), self.path))
        if self.args.strip():
            parts[-1] += " " + self.args.strip()
        parts.append('echo "[进程已退出] 退出码: $?"')
        return " && ".join(parts)

    def start(self, ros_setup, ws_setup, log_callback, finish_callback):
        if self.is_running():
            return
        cmd = self.build_command(ros_setup, ws_setup)
        if self.process is not None:
            self.process.deleteLater()  # 释放旧的 QProcess,避免泄漏
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(
            lambda: log_callback(self, self.process.readAllStandardOutput().data().decode(errors="replace"))
        )
        self.process.finished.connect(lambda code, status: finish_callback(self))
        # 用 setsid 让任务成为独立进程组的组长(pgid == pid),
        # 停止时 killpg 可以杀掉 roslaunch/gazebo 等所有子孙进程
        self.process.start("setsid", ["bash", "-c", cmd])

    def stop(self):
        self.stop_requested = True
        if not (self.process and self.is_running()):
            return
        # 进程组的 pgid 等于组长进程 pid;killpg 给全组(含所有子孙进程)发信号
        pid = self.process.processId()
        killed = False
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
                killed = True
            except OSError:
                pass
        if not killed:
            self.process.terminate()
        if not self.process.waitForFinished(2500):
            if pid:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
            self.process.kill()

    def is_running(self):
        return self.process is not None and self.process.state() == QProcess.Running

    def exists(self, cache=None):
        if cache is not None and self.path in cache:
            return cache[self.path]
        result = os.path.isfile(self.path)
        if cache is not None:
            cache[self.path] = result
        return result

    def to_dict(self):
        return {
            "path": self.path,
            "args": self.args,
            "auto_restart": self.auto_restart,
            "auto_start": self.auto_start,
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROS 一键启动器 v%s" % VERSION)
        self.resize(1400, 900)
        self._load_style()
        self.config = self.load_config()
        self._loading = False
        self._log_file = None
        self._file_exists_cache = {}
        self.security = SecurityManager()
        self.monitor = ProcessMonitor()
        self.updater = Updater(VERSION)
        self.log_manager = LogManager(LOG_DIR)
        self.translator = ROSTranslator()
        self.scene_manager = SceneManager(config_dir=BASE_DIR)
        self.ros_monitor = ROSMonitor(
            ros_setup=self.config.get("ros_setup", ""),
            ws_setup=self.config.get("ws_setup", "")
        )
        self.task_scheduler = TaskScheduler(config_dir=BASE_DIR)
        self.sim_controller = SimulationController()
        self.log_analyzer = LogAnalyzer(LOG_DIR)
        self.tf_monitor = TFMonitor()
        self.data_visualizer = DataVisualizer()
        self.multi_machine = MultiMachineController(config_dir=BASE_DIR)
        self.plugin_manager = PluginManager(config_dir=BASE_DIR)
        self._check_platform()

        # 状态栏
        self._status_label = QLabel("就绪")
        self._status_running = QLabel("运行中: 0")
        self._status_task = QLabel("任务: 0")
        status_bar = self.statusBar()
        status_bar.addWidget(self._status_label, 1)
        status_bar.addPermanentWidget(self._status_task)
        status_bar.addPermanentWidget(self._status_running)

        central = QWidget()
        self.setCentralWidget(central)
        self._main_layout = QVBoxLayout(central)

        # ---- 全局操作 (轻量级,立即初始化) ----
        global_row = QHBoxLayout()
        start_everything = QPushButton("▶  一键启动所有任务")
        start_everything.setObjectName("btnGlobalStart")
        start_everything.setMinimumHeight(46)
        start_everything.clicked.connect(self.start_everything)
        stop_everything = QPushButton("■  停止所有任务")
        stop_everything.setObjectName("btnGlobalStop")
        stop_everything.setMinimumHeight(46)
        stop_everything.clicked.connect(self.stop_everything)
        global_row.addWidget(start_everything)
        global_row.addWidget(stop_everything)
        global_row.addStretch(1)
        
        # 配置导入导出按钮
        import_btn = QPushButton("📥 导入配置")
        import_btn.clicked.connect(self.import_config)
        export_btn = QPushButton("📤 导出配置")
        export_btn.clicked.connect(self.export_config)
        global_row.addWidget(import_btn)
        global_row.addWidget(export_btn)
        
        # 远程更新按钮
        update_btn = QPushButton("🔄 检查更新")
        update_btn.clicked.connect(self.check_update)
        global_row.addWidget(update_btn)
        
        # 多配置切换
        self.config_combo = QComboBox()
        self.config_combo.setMinimumWidth(150)
        self.config_combo.currentTextChanged.connect(self._on_config_changed)
        global_row.addWidget(QLabel("配置:"))
        global_row.addWidget(self.config_combo)
        
        save_config_btn = QPushButton("💾 保存配置")
        save_config_btn.clicked.connect(self._save_current_config)
        global_row.addWidget(save_config_btn)
        
        self._main_layout.addLayout(global_row)
        
        # 全局进度条
        self.global_progress = QProgressBar()
        self.global_progress.setRange(0, 100)
        self.global_progress.setValue(0)
        self.global_progress.hide()
        self.global_progress.setMaximumHeight(6)
        self._main_layout.addWidget(self.global_progress)
        
        # 批量操作按钮
        batch_row = QHBoxLayout()
        
        batch_select_all = QPushButton("全选")
        batch_select_all.clicked.connect(self._batch_select_all)
        batch_row.addWidget(batch_select_all)
        
        batch_deselect_all = QPushButton("取消全选")
        batch_deselect_all.clicked.connect(self._batch_deselect_all)
        batch_row.addWidget(batch_deselect_all)
        
        batch_enable_restart = QPushButton("启用崩溃重启")
        batch_enable_restart.clicked.connect(lambda: self._batch_set_restart(True))
        batch_row.addWidget(batch_enable_restart)
        
        batch_disable_restart = QPushButton("禁用崩溃重启")
        batch_disable_restart.clicked.connect(lambda: self._batch_set_restart(False))
        batch_row.addWidget(batch_disable_restart)
        
        batch_enable_autostart = QPushButton("启用自启动")
        batch_enable_autostart.clicked.connect(lambda: self._batch_set_autostart(True))
        batch_row.addWidget(batch_enable_autostart)
        
        batch_disable_autostart = QPushButton("禁用自启动")
        batch_disable_autostart.clicked.connect(lambda: self._batch_set_autostart(False))
        batch_row.addWidget(batch_disable_autostart)
        
        batch_row.addStretch()
        
        # 快捷键说明
        hotkey_label = QLabel("快捷键: F5启动 | F6停止 | F7启动选中 | F8停止选中")
        hotkey_label.setStyleSheet("color: #8ab4f8; font-size: 11px;")
        batch_row.addWidget(hotkey_label)
        
        self._main_layout.addLayout(batch_row)

        # ---- ROS 环境设置 (轻量级,立即初始化) ----
        env_box = QGroupBox("ROS 环境 (source 路径)")
        env_layout = QVBoxLayout(env_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("ROS setup:"))
        self.ros_setup_edit = QLineEdit(self.config["ros_setup"])
        self.ros_setup_edit.editingFinished.connect(self.save_config)
        row1.addWidget(self.ros_setup_edit)
        btn = QPushButton("浏览")
        btn.clicked.connect(lambda: self.browse_file(self.ros_setup_edit))
        row1.addWidget(btn)
        env_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("工作空间 devel:"))
        self.ws_setup_edit = QLineEdit(self.config["ws_setup"])
        self.ws_setup_edit.setPlaceholderText("可选,例如 ~/catkin_ws/devel/setup.bash")
        self.ws_setup_edit.editingFinished.connect(self.save_config)
        row2.addWidget(self.ws_setup_edit)
        btn2 = QPushButton("浏览")
        btn2.clicked.connect(lambda: self.browse_file(self.ws_setup_edit))
        row2.addWidget(btn2)
        env_layout.addLayout(row2)
        self._main_layout.addWidget(env_box)

        # ---- launch/py 文件并排管理 (水平分割,可拖动) ----
        self.task_splitter = QSplitter(Qt.Horizontal)
        self.task_splitter.setChildrenCollapsible(False)
        self.task_splitter.setHandleWidth(6)

        self.launch_table, launch_box = self._make_task_group(
            "Launch 文件 (roslaunch)", "launch")
        self.py_table, py_box = self._make_task_group(
            "Python 文件 (python3)", "py")

        self.task_splitter.addWidget(launch_box)
        self.task_splitter.addWidget(py_box)
        self.task_splitter.setStretchFactor(0, 1)
        self.task_splitter.setStretchFactor(1, 1)
        self.task_splitter.setSizes([600, 600])

        # ---- 任务区 + 日志区 垂直分割,可拖动 ----
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.addWidget(self.task_splitter)

        # ---- 日志/标签页 (延迟初始化,重量级组件) ----
        self._log_box_placeholder = QWidget()
        self.main_splitter.addWidget(self._log_box_placeholder)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 3)
        self.main_splitter.setSizes([450, 650])

        # ---- 左侧导航栏 + 右侧内容区 ----
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(190)
        self.nav_list.setObjectName("navList")
        self.content_stack = QStackedWidget()

        self._nav_container = QWidget()
        nav_layout = QHBoxLayout(self._nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)
        nav_layout.addWidget(self.nav_list)
        nav_layout.addWidget(self.content_stack, 1)

        self._main_layout.addWidget(self._nav_container)

        # 恢复已保存的文件列表
        self._loading = True
        for entry in list(self.config["launch_files"]):
            self._add_row(self.launch_table, normalize_task(entry), "launch")
        for entry in list(self.config["py_files"]):
            self._add_row(self.py_table, normalize_task(entry), "py")
        self._loading = False

        # 延迟初始化重量级组件:日志视图 + 文件存在性检查
        QTimer.singleShot(0, self._init_heavy_components)

    # ---------- 延迟初始化 ----------

    def _load_style(self):
        """加载样式表:优先外部 style.qss,打包后回退到内置主题"""
        style_path = os.path.join(BASE_DIR, "style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            self.setStyleSheet(APP_QSS)

    def _init_heavy_components(self):
        """延迟初始化重量级组件"""
        # 延迟初始化日志视图
        self._init_log_file()
        
        # 左侧导航 + 右侧内容区(替代原QTabWidget)
        self.tab_widget = self.content_stack
        self._nav_index = {}
        self._nav_pages = []
        
        def add_page(widget, name):
            """添加页面到内容区,并在导航栏显示"""
            self.content_stack.addWidget(widget)
            self.nav_list.addItem(name)
            self._nav_pages.append(widget)
        
        self._add_page = add_page
        
        # 运行日志页(直接放到main_splitter下部,不占导航)
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        log_layout.addWidget(self.log_view)
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_view.clear)
        log_layout.addWidget(clear_btn)
        
        # 任务管理页 = main_splitter(launch/py + 日志)
        idx = self.main_splitter.indexOf(self._log_box_placeholder)
        if idx >= 0:
            self.main_splitter.replaceWidget(idx, log_widget)
            self._log_box_placeholder.deleteLater()
        add_page(self.main_splitter, "📋 任务管理")
        
        # 监控页
        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout(monitor_widget)
        
        # 系统资源监控
        sys_group = QGroupBox("系统资源 (实时)")
        sys_layout = QVBoxLayout(sys_group)
        
        # 实时趋势图
        self.trend_chart = TrendChartWidget()
        self.trend_chart.add_series("cpu", color="#8be9fd", label="CPU")
        self.trend_chart.add_series("memory", color="#bd93f9", label="内存")
        sys_layout.addWidget(self.trend_chart)
        
        # 当前值显示
        values_layout = QHBoxLayout()
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_label.setStyleSheet("color: #8be9fd; font-size: 14px; font-weight: bold;")
        values_layout.addWidget(self.cpu_label)
        values_layout.addStretch()
        self.mem_label = QLabel("内存: 0%")
        self.mem_label.setStyleSheet("color: #bd93f9; font-size: 14px; font-weight: bold;")
        values_layout.addWidget(self.mem_label)
        values_layout.addStretch()
        values_layout.addWidget(QLabel(""))
        sys_layout.addLayout(values_layout)
        
        monitor_layout.addWidget(sys_group)
        
        # 进程状态
        proc_group = QGroupBox("运行中的进程")
        proc_layout = QVBoxLayout(proc_group)
        self.proc_list = QPlainTextEdit()
        self.proc_list.setReadOnly(True)
        self.proc_list.setMaximumHeight(150)
        proc_layout.addWidget(self.proc_list)
        monitor_layout.addWidget(proc_group)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新监控")
        refresh_btn.clicked.connect(self.refresh_monitor)
        monitor_layout.addWidget(refresh_btn)
        
        add_page(monitor_widget, "📊 系统监控")
        
        # 历史记录标签页
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        history_label = QLabel("双击项目可快速加载:")
        history_layout.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._on_history_clicked)
        history_layout.addWidget(self.history_list)
        
        history_btn_layout = QHBoxLayout()
        clear_history_btn = QPushButton("清空历史")
        clear_history_btn.clicked.connect(self._clear_history)
        history_btn_layout.addWidget(clear_history_btn)
        history_btn_layout.addStretch()
        history_layout.addLayout(history_btn_layout)
        
        add_page(history_widget, "🕘 历史记录")
        
        # 内置终端标签页
        self.terminal_widget = TerminalWidget(
            ros_setup=self.config.get("ros_setup", ""),
            ws_setup=self.config.get("ws_setup", "")
        )
        add_page(self.terminal_widget, "💻 内置终端")
        
        # 场景管理标签页
        scene_widget = QWidget()
        scene_layout = QVBoxLayout(scene_widget)
        
        scene_btn_layout = QHBoxLayout()
        create_scene_btn = QPushButton("创建场景")
        create_scene_btn.clicked.connect(self._create_scene)
        scene_btn_layout.addWidget(create_scene_btn)
        
        save_scene_btn = QPushButton("保存当前为场景")
        save_scene_btn.clicked.connect(self._save_current_as_scene)
        scene_btn_layout.addWidget(save_scene_btn)
        
        scene_btn_layout.addStretch()
        scene_layout.addLayout(scene_btn_layout)
        
        self.scene_list = QListWidget()
        self.scene_list.itemDoubleClicked.connect(self._on_scene_clicked)
        scene_layout.addWidget(self.scene_list)
        
        scene_action_layout = QHBoxLayout()
        apply_scene_btn = QPushButton("应用场景")
        apply_scene_btn.clicked.connect(self._apply_scene)
        scene_action_layout.addWidget(apply_scene_btn)
        
        delete_scene_btn = QPushButton("删除场景")
        delete_scene_btn.clicked.connect(self._delete_scene)
        scene_action_layout.addWidget(delete_scene_btn)
        
        scene_action_layout.addStretch()
        scene_layout.addLayout(scene_action_layout)
        
        add_page(scene_widget, "🎬 场景管理")
        
        # 翻译工具标签页
        translator_widget = QWidget()
        translator_layout = QVBoxLayout(translator_widget)
        
        translator_input_layout = QHBoxLayout()
        translator_input_layout.addWidget(QLabel("输入英文:"))
        self.translator_input = QLineEdit()
        self.translator_input.setPlaceholderText("输入要翻译的ROS错误信息...")
        translator_input_layout.addWidget(self.translator_input)
        
        translate_btn = QPushButton("翻译")
        translate_btn.clicked.connect(self._translate_text)
        translator_input_layout.addWidget(translate_btn)
        
        translator_layout.addLayout(translator_input_layout)
        
        translator_output_layout = QHBoxLayout()
        translator_output_layout.addWidget(QLabel("中文翻译:"))
        self.translator_output = QLineEdit()
        self.translator_output.setReadOnly(True)
        translator_output_layout.addWidget(self.translator_output)
        
        copy_btn = QPushButton("复制")
        copy_btn.clicked.connect(self._copy_translation)
        translator_output_layout.addWidget(copy_btn)
        
        translator_layout.addLayout(translator_output_layout)
        
        # 翻译开关
        self.translation_enabled_cb = QPushButton("启用自动翻译")
        self.translation_enabled_cb.setCheckable(True)
        self.translation_enabled_cb.setChecked(self.config.get("translation_enabled", True))
        self.translation_enabled_cb.clicked.connect(self._toggle_translation)
        translator_layout.addWidget(self.translation_enabled_cb)
        
        translator_layout.addStretch()
        
        add_page(translator_widget, "🌐 翻译工具")
        
        # ROS监控标签页
        ros_monitor_widget = QWidget()
        ros_monitor_layout = QVBoxLayout(ros_monitor_widget)
        
        # ROS主节点状态
        master_group = QGroupBox("ROS主节点状态")
        master_layout = QHBoxLayout(master_group)
        
        self.ros_master_status = QLabel("状态: 未知")
        master_layout.addWidget(self.ros_master_status)
        
        refresh_master_btn = QPushButton("刷新状态")
        refresh_master_btn.clicked.connect(self._refresh_ros_master)
        master_layout.addWidget(refresh_master_btn)
        
        ros_monitor_layout.addWidget(master_group)
        
        # 节点监控
        node_group = QGroupBox("ROS节点监控")
        node_layout = QVBoxLayout(node_group)
        
        node_btn_layout = QHBoxLayout()
        refresh_nodes_btn = QPushButton("刷新节点列表")
        refresh_nodes_btn.clicked.connect(self._refresh_ros_nodes)
        node_btn_layout.addWidget(refresh_nodes_btn)
        
        node_info_btn = QPushButton("查看节点信息")
        node_info_btn.clicked.connect(self._show_node_info)
        node_btn_layout.addWidget(node_info_btn)
        
        node_btn_layout.addStretch()
        node_layout.addLayout(node_btn_layout)
        
        self.node_tree = QTreeWidget()
        self.node_tree.setHeaderLabels(["节点名称", "状态", "发布者", "订阅者"])
        self.node_tree.setAlternatingRowColors(True)
        node_layout.addWidget(self.node_tree)
        
        ros_monitor_layout.addWidget(node_group)
        
        # Topic监控
        topic_group = QGroupBox("ROS Topic监控")
        topic_layout = QVBoxLayout(topic_group)
        
        topic_btn_layout = QHBoxLayout()
        refresh_topics_btn = QPushButton("刷新Topic列表")
        refresh_topics_btn.clicked.connect(self._refresh_ros_topics)
        topic_btn_layout.addWidget(refresh_topics_btn)
        
        topic_info_btn = QPushButton("查看Topic信息")
        topic_info_btn.clicked.connect(self._show_topic_info)
        topic_btn_layout.addWidget(topic_info_btn)
        
        topic_btn_layout.addStretch()
        topic_layout.addLayout(topic_btn_layout)
        
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderLabels(["Topic名称", "类型", "发布者数", "订阅者数"])
        self.topic_tree.setAlternatingRowColors(True)
        topic_layout.addWidget(self.topic_tree)
        
        ros_monitor_layout.addWidget(topic_group)
        
        # 网络监控
        network_group = QGroupBox("网络监控")
        network_layout = QVBoxLayout(network_group)
        
        self.network_info = QPlainTextEdit()
        self.network_info.setReadOnly(True)
        self.network_info.setMaximumHeight(100)
        network_layout.addWidget(self.network_info)
        
        refresh_network_btn = QPushButton("刷新网络状态")
        refresh_network_btn.clicked.connect(self._refresh_network)
        network_layout.addWidget(refresh_network_btn)
        
        ros_monitor_layout.addWidget(network_group)
        
        add_page(ros_monitor_widget, "🤖 ROS监控")
        
        # 磁盘监控标签页
        disk_widget = QWidget()
        disk_layout = QVBoxLayout(disk_widget)
        
        # 磁盘使用情况
        disk_group = QGroupBox("磁盘使用情况")
        disk_inner_layout = QVBoxLayout(disk_group)
        
        self.disk_tree = QTreeWidget()
        self.disk_tree.setHeaderLabels(["设备", "挂载点", "总大小", "已用", "可用", "使用率"])
        self.disk_tree.setAlternatingRowColors(True)
        disk_inner_layout.addWidget(self.disk_tree)
        
        refresh_disk_btn = QPushButton("刷新磁盘信息")
        refresh_disk_btn.clicked.connect(self._refresh_disk)
        disk_inner_layout.addWidget(refresh_disk_btn)
        
        disk_layout.addWidget(disk_group)
        
        # 日志目录大小
        log_size_group = QGroupBox("日志目录")
        log_size_layout = QHBoxLayout(log_size_group)
        
        self.log_size_label = QLabel("日志目录大小: 计算中...")
        log_size_layout.addWidget(self.log_size_label)
        
        refresh_log_size_btn = QPushButton("刷新")
        refresh_log_size_btn.clicked.connect(self._refresh_log_size)
        log_size_layout.addWidget(refresh_log_size_btn)
        
        clean_logs_btn = QPushButton("清理旧日志")
        clean_logs_btn.clicked.connect(self._clean_old_logs)
        log_size_layout.addWidget(clean_logs_btn)
        
        log_size_layout.addStretch()
        disk_layout.addWidget(log_size_group)
        
        disk_layout.addStretch()
        
        add_page(disk_widget, "💾 磁盘监控")
        
        # TF可视化标签页
        try:
            from tf_visualizer import TFVisualizerWidget
            self.tf_visualizer = TFVisualizerWidget(
                ros_setup=self.config.get("ros_setup", ""),
                ws_setup=self.config.get("ws_setup", "")
            )
            add_page(self.tf_visualizer, "🧭 TF可视化")
        except Exception as e:
            print(f"加载TF可视化组件失败: {e}")
        
        # 任务调度标签页
        scheduler_widget = QWidget()
        scheduler_layout = QVBoxLayout(scheduler_widget)
        
        scheduler_btn_layout = QHBoxLayout()
        add_schedule_btn = QPushButton("添加定时任务")
        add_schedule_btn.clicked.connect(self._add_schedule)
        scheduler_btn_layout.addWidget(add_schedule_btn)
        
        refresh_schedule_btn = QPushButton("刷新列表")
        refresh_schedule_btn.clicked.connect(self._refresh_schedules)
        scheduler_btn_layout.addWidget(refresh_schedule_btn)
        
        scheduler_btn_layout.addStretch()
        scheduler_layout.addLayout(scheduler_btn_layout)
        
        self.schedule_tree = QTreeWidget()
        self.schedule_tree.setHeaderLabels(["任务名称", "类型", "路径", "状态", "下次运行"])
        self.schedule_tree.setAlternatingRowColors(True)
        scheduler_layout.addWidget(self.schedule_tree)
        
        add_page(scheduler_widget, "⏰ 任务调度")
        
        # 仿真控制标签页
        sim_widget = QWidget()
        sim_layout = QVBoxLayout(sim_widget)
        
        sim_group = QGroupBox("Gazebo仿真控制")
        sim_inner_layout = QHBoxLayout(sim_group)
        
        pause_sim_btn = QPushButton("暂停仿真")
        pause_sim_btn.clicked.connect(self._pause_simulation)
        sim_inner_layout.addWidget(pause_sim_btn)
        
        unpause_sim_btn = QPushButton("继续仿真")
        unpause_sim_btn.clicked.connect(self._unpause_simulation)
        sim_inner_layout.addWidget(unpause_sim_btn)
        
        reset_sim_btn = QPushButton("重置仿真")
        reset_sim_btn.clicked.connect(self._reset_simulation)
        sim_inner_layout.addWidget(reset_sim_btn)
        
        sim_layout.addWidget(sim_group)
        
        # 模型管理
        model_group = QGroupBox("模型管理")
        model_layout = QVBoxLayout(model_group)
        
        model_btn_layout = QHBoxLayout()
        spawn_model_btn = QPushButton("生成模型")
        spawn_model_btn.clicked.connect(self._spawn_model)
        model_btn_layout.addWidget(spawn_model_btn)
        
        delete_model_btn = QPushButton("删除模型")
        delete_model_btn.clicked.connect(self._delete_model)
        model_btn_layout.addWidget(delete_model_btn)
        
        model_btn_layout.addStretch()
        model_layout.addLayout(model_btn_layout)
        
        sim_layout.addWidget(model_group)
        sim_layout.addStretch()
        
        add_page(sim_widget, "🎮 仿真控制")
        
        # 日志分析标签页
        analyzer_widget = QWidget()
        analyzer_layout = QVBoxLayout(analyzer_widget)
        
        analyzer_btn_layout = QHBoxLayout()
        analyze_all_btn = QPushButton("分析所有日志")
        analyze_all_btn.clicked.connect(self._analyze_all_logs)
        analyzer_btn_layout.addWidget(analyze_all_btn)
        
        search_errors_btn = QPushButton("搜索错误")
        search_errors_btn.clicked.connect(self._search_errors)
        analyzer_btn_layout.addWidget(search_errors_btn)
        
        export_report_btn = QPushButton("导出报告")
        export_report_btn.clicked.connect(self._export_report)
        analyzer_btn_layout.addWidget(export_report_btn)
        
        analyzer_btn_layout.addStretch()
        analyzer_layout.addLayout(analyzer_btn_layout)
        
        self.analysis_result = QPlainTextEdit()
        self.analysis_result.setReadOnly(True)
        analyzer_layout.addWidget(self.analysis_result)
        
        add_page(analyzer_widget, "🔍 日志分析")
        
        # 多机协同标签页
        multi_machine_widget = QWidget()
        multi_machine_layout = QVBoxLayout(multi_machine_widget)
        
        # 上半部分：机器列表
        machine_list_layout = QHBoxLayout()
        
        # 左侧按钮
        machine_btn_layout = QVBoxLayout()
        add_machine_btn = QPushButton("添加机器")
        add_machine_btn.clicked.connect(self._add_machine)
        machine_btn_layout.addWidget(add_machine_btn)
        
        remove_machine_btn = QPushButton("删除机器")
        remove_machine_btn.clicked.connect(self._remove_machine)
        machine_btn_layout.addWidget(remove_machine_btn)
        
        test_connection_btn = QPushButton("测试连接")
        test_connection_btn.clicked.connect(self._test_machine_connection)
        machine_btn_layout.addWidget(test_connection_btn)
        
        setup_key_btn = QPushButton("设置密钥")
        setup_key_btn.clicked.connect(self._setup_machine_key)
        machine_btn_layout.addWidget(setup_key_btn)
        
        refresh_machines_btn = QPushButton("刷新列表")
        refresh_machines_btn.clicked.connect(self._refresh_machines)
        machine_btn_layout.addWidget(refresh_machines_btn)
        
        machine_btn_layout.addStretch()
        machine_list_layout.addLayout(machine_btn_layout)
        
        # 右侧机器列表
        self.machine_tree = QTreeWidget()
        self.machine_tree.setHeaderLabels(["名称", "主机名", "用户名", "端口", "状态"])
        self.machine_tree.setAlternatingRowColors(True)
        self.machine_tree.itemSelectionChanged.connect(self._on_machine_selected)
        machine_list_layout.addWidget(self.machine_tree)
        
        multi_machine_layout.addLayout(machine_list_layout)
        
        # 下半部分：ROS远程控制
        ros_remote_group = QGroupBox("ROS远程控制")
        ros_remote_layout = QVBoxLayout(ros_remote_group)
        
        # ROS控制按钮
        ros_btn_layout = QHBoxLayout()
        
        start_master_btn = QPushButton("启动roscore")
        start_master_btn.clicked.connect(self._remote_start_master)
        ros_btn_layout.addWidget(start_master_btn)
        
        stop_master_btn = QPushButton("停止roscore")
        stop_master_btn.clicked.connect(self._remote_stop_master)
        ros_btn_layout.addWidget(stop_master_btn)
        
        start_launch_btn = QPushButton("启动launch")
        start_launch_btn.clicked.connect(self._remote_start_launch)
        ros_btn_layout.addWidget(start_launch_btn)
        
        stop_launch_btn = QPushButton("停止launch")
        stop_launch_btn.clicked.connect(self._remote_stop_launch)
        ros_btn_layout.addWidget(stop_launch_btn)
        
        ros_remote_layout.addLayout(ros_btn_layout)
        
        # 远程文件浏览器
        file_browser_group = QGroupBox("远程文件浏览器")
        file_browser_layout = QVBoxLayout(file_browser_group)
        
        # 路径导航
        path_layout = QHBoxLayout()
        
        home_btn = QPushButton("主目录")
        home_btn.clicked.connect(self._remote_go_home)
        path_layout.addWidget(home_btn)
        
        back_btn = QPushButton("返回上级")
        back_btn.clicked.connect(self._remote_go_back)
        path_layout.addWidget(back_btn)
        
        self.remote_path_edit = QLineEdit()
        self.remote_path_edit.setPlaceholderText("远程路径...")
        self.remote_path_edit.returnPressed.connect(self._remote_goto_path)
        path_layout.addWidget(self.remote_path_edit)
        
        goto_btn = QPushButton("跳转")
        goto_btn.clicked.connect(self._remote_goto_path)
        path_layout.addWidget(goto_btn)
        
        refresh_file_btn = QPushButton("刷新")
        refresh_file_btn.clicked.connect(self._refresh_remote_files)
        path_layout.addWidget(refresh_file_btn)
        
        file_browser_layout.addLayout(path_layout)
        
        # 文件列表
        file_list_layout = QHBoxLayout()
        
        # 目录树
        self.remote_dir_tree = QTreeWidget()
        self.remote_dir_tree.setHeaderLabels(["名称", "大小", "类型", "修改时间"])
        self.remote_dir_tree.setAlternatingRowColors(True)
        self.remote_dir_tree.itemDoubleClicked.connect(self._remote_file_double_clicked)
        self.remote_dir_tree.itemSelectionChanged.connect(self._remote_file_selected)
        file_list_layout.addWidget(self.remote_dir_tree)
        
        # 右侧按钮
        file_btn_layout = QVBoxLayout()
        
        run_btn = QPushButton("运行此文件")
        run_btn.clicked.connect(self._remote_run_selected_file)
        file_btn_layout.addWidget(run_btn)
        
        add_launch_btn = QPushButton("添加到launch")
        add_launch_btn.clicked.connect(self._remote_add_to_launch)
        file_btn_layout.addWidget(add_launch_btn)
        
        add_py_btn = QPushButton("添加到py")
        add_py_btn.clicked.connect(self._remote_add_to_py)
        file_btn_layout.addWidget(add_py_btn)
        
        file_btn_layout.addStretch()
        
        # 搜索功能
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索文件...")
        search_layout.addWidget(self.search_edit)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._remote_search_files)
        search_layout.addWidget(search_btn)
        file_btn_layout.addLayout(search_layout)
        
        file_list_layout.addLayout(file_btn_layout)
        file_browser_layout.addLayout(file_list_layout)
        
        ros_remote_layout.addWidget(file_browser_group)
        
        # ROS信息显示
        ros_info_layout = QHBoxLayout()
        
        # 节点列表
        nodes_group = QGroupBox("ROS节点")
        nodes_layout = QVBoxLayout(nodes_group)
        self.remote_nodes_list = QListWidget()
        nodes_layout.addWidget(self.remote_nodes_list)
        
        refresh_nodes_btn = QPushButton("刷新节点")
        refresh_nodes_btn.clicked.connect(self._refresh_remote_nodes)
        nodes_layout.addWidget(refresh_nodes_btn)
        
        ros_info_layout.addWidget(nodes_group)
        
        # 话题列表
        topics_group = QGroupBox("ROS话题")
        topics_layout = QVBoxLayout(topics_group)
        self.remote_topics_list = QListWidget()
        topics_layout.addWidget(self.remote_topics_list)
        
        refresh_topics_btn = QPushButton("刷新话题")
        refresh_topics_btn.clicked.connect(self._refresh_remote_topics)
        topics_layout.addWidget(refresh_topics_btn)
        
        ros_info_layout.addWidget(topics_group)
        
        ros_remote_layout.addLayout(ros_info_layout)
        
        # 机器人状态
        status_layout = QHBoxLayout()
        
        self.remote_cpu_label = QLabel("CPU: --")
        status_layout.addWidget(self.remote_cpu_label)
        
        self.remote_mem_label = QLabel("内存: --")
        status_layout.addWidget(self.remote_mem_label)
        
        self.remote_disk_label = QLabel("磁盘: --")
        status_layout.addWidget(self.remote_disk_label)
        
        self.remote_uptime_label = QLabel("运行时间: --")
        status_layout.addWidget(self.remote_uptime_label)
        
        refresh_status_btn = QPushButton("刷新状态")
        refresh_status_btn.clicked.connect(self._refresh_robot_status)
        status_layout.addWidget(refresh_status_btn)
        
        ros_remote_layout.addLayout(status_layout)
        
        # 自定义命令执行
        custom_cmd_layout = QHBoxLayout()
        
        self.custom_cmd_edit = QLineEdit()
        self.custom_cmd_edit.setPlaceholderText("输入要执行的远程命令...")
        custom_cmd_layout.addWidget(self.custom_cmd_edit)
        
        exec_cmd_btn = QPushButton("执行")
        exec_cmd_btn.clicked.connect(self._execute_remote_command)
        custom_cmd_layout.addWidget(exec_cmd_btn)
        
        ros_remote_layout.addLayout(custom_cmd_layout)
        
        # 命令输出显示
        self.cmd_output = QPlainTextEdit()
        self.cmd_output.setReadOnly(True)
        self.cmd_output.setMaximumHeight(100)
        ros_remote_layout.addWidget(self.cmd_output)
        
        multi_machine_layout.addWidget(ros_remote_group)
        
        add_page(multi_machine_widget, "🌍 多机协同")
        
        # 插件管理标签页
        plugin_widget = QWidget()
        plugin_layout = QVBoxLayout(plugin_widget)
        
        plugin_btn_layout = QHBoxLayout()
        discover_plugins_btn = QPushButton("发现插件")
        discover_plugins_btn.clicked.connect(self._discover_plugins)
        plugin_btn_layout.addWidget(discover_plugins_btn)
        
        load_plugin_btn = QPushButton("加载插件")
        load_plugin_btn.clicked.connect(self._load_plugin)
        plugin_btn_layout.addWidget(load_plugin_btn)
        
        refresh_plugins_btn = QPushButton("刷新列表")
        refresh_plugins_btn.clicked.connect(self._refresh_plugins)
        plugin_btn_layout.addWidget(refresh_plugins_btn)
        
        plugin_btn_layout.addStretch()
        plugin_layout.addLayout(plugin_btn_layout)
        
        self.plugin_tree = QTreeWidget()
        self.plugin_tree.setHeaderLabels(["插件名称", "状态", "描述", "版本"])
        self.plugin_tree.setAlternatingRowColors(True)
        plugin_layout.addWidget(self.plugin_tree)
        
        add_page(plugin_widget, "🧩 插件管理")
        
        # ===== 新增功能模块 =====
        ros_env = (
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        
        try:
            from robot_control import RobotControlWidget
            self.robot_control = RobotControlWidget(*ros_env)
            self.robot_control.set_ros_env(*ros_env)
            add_page(self.robot_control, "🎮 遥控面板")
        except Exception as e:
            self.log(f"加载遥控面板失败: {e}")
        
        try:
            from navigation_panel import NavigationWidget
            self.navigation_panel = NavigationWidget(*ros_env)
            add_page(self.navigation_panel, "🧭 一键导航")
        except Exception as e:
            self.log(f"加载一键导航失败: {e}")
        
        try:
            from sensor_panel import SensorPanelWidget
            self.sensor_panel = SensorPanelWidget(*ros_env)
            add_page(self.sensor_panel, "📡 传感器面板")
        except Exception as e:
            self.log(f"加载传感器面板失败: {e}")
        
        try:
            from camera_view import CameraViewWidget
            self.camera_view = CameraViewWidget(*ros_env)
            add_page(self.camera_view, "📷 摄像头画面")
        except Exception as e:
            self.log(f"加载摄像头画面失败: {e}")
        
        try:
            from topic_table import TopicTableWidget
            self.topic_table = TopicTableWidget(*ros_env)
            add_page(self.topic_table, "📊 话题数据表")
        except Exception as e:
            self.log(f"加载话题数据表失败: {e}")
        
        try:
            from bag_manager import BagManagerWidget
            self.bag_manager = BagManagerWidget(*ros_env)
            add_page(self.bag_manager, "📼 rosbag管理")
        except Exception as e:
            self.log(f"加载rosbag管理失败: {e}")
        
        try:
            from alarm_system import AlarmSystemWidget
            self.alarm_system = AlarmSystemWidget(*ros_env)
            # 关联监控的launch/py任务
            monitored = []
            for kind in ("launch", "py"):
                for r, task, item in self._rows_of(self._table_of(kind)):
                    if task.path:
                        monitored.append(task.path)
            self.alarm_system.set_monitored_nodes(monitored)
            add_page(self.alarm_system, "🔔 报警系统")
        except Exception as e:
            self.log(f"加载报警系统失败: {e}")
        
        try:
            from serial_debug import SerialDebugWidget
            self.serial_debug = SerialDebugWidget()
            add_page(self.serial_debug, "🔌 串口调试")
        except Exception as e:
            self.log(f"加载串口调试失败: {e}")
        
        try:
            from web_remote import WebRemoteWidget
            self.web_remote = WebRemoteWidget(*ros_env)
            add_page(self.web_remote, "🌐 Web远程")
        except Exception as e:
            self.log(f"加载Web远程失败: {e}")
        
        # 导航栏点击切换页面
        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)
        
        # 加载历史记录
        self._load_history()
        
        # 加载场景列表
        self._load_scene_list()
        
        # 加载配置列表
        self._load_config_list()
        
        # 绑定快捷键
        self._setup_hotkeys()
        
        # 延迟刷新文件存在性
        self.refresh_file_existence()
        
        # 打开软件后自动启动勾选了的任务(延时错开)
        QTimer.singleShot(1000, self.auto_start_tasks)
        
        # 启动监控定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.refresh_monitor)
        self.monitor_timer.start(5000)  # 每5秒刷新一次
        
        # 启用拖拽支持
        self.setAcceptDrops(True)
        
        # 启动ROS监控定时器
        self.ros_monitor_timer = QTimer()
        self.ros_monitor_timer.timeout.connect(self._auto_refresh_ros_monitor)
        self.ros_monitor_timer.start(10000)  # 每10秒刷新一次

    # ---------- UI 构建 ----------

    def _make_task_group(self, title, kind):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["状态", "文件路径", "启动参数", "崩溃重启", "自启动", "操作"])
        table.horizontalHeader().setSectionResizeMode(COL_PATH, QHeaderView.Stretch)
        table.setColumnWidth(COL_STATUS, 90)
        table.setColumnWidth(COL_RESTART, 70)
        table.setColumnWidth(COL_AUTOSTART, 70)
        table.setColumnWidth(COL_OPS, 170)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.itemChanged.connect(
            lambda item, k=kind: self.on_item_changed(k, item))
        layout.addWidget(table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加文件")
        add_btn.clicked.connect(lambda: self.add_file(kind))
        start_btn = QPushButton("启动选中")
        start_btn.clicked.connect(lambda: self.start_selected(kind))
        stop_btn = QPushButton("停止选中")
        stop_btn.clicked.connect(lambda: self.stop_selected(kind))
        remove_btn = QPushButton("移除选中")
        remove_btn.clicked.connect(lambda: self.remove_selected(kind))
        start_all = QPushButton("顺序启动全部")
        start_all.clicked.connect(lambda: self.start_all(kind))
        stop_all = QPushButton("全部停止")
        stop_all.clicked.connect(lambda: self.stop_all(kind))
        for b in (add_btn, start_btn, stop_btn, remove_btn, start_all, stop_all):
            btns.addWidget(b)
        btns.addStretch(1)
        btns.addWidget(QLabel("顺序延时(秒):"))
        delay_spin = QSpinBox()
        delay_spin.setRange(0, 120)
        delay_spin.setValue(int(self.config.get("start_delay", 3)))
        delay_spin.valueChanged.connect(self.on_delay_changed)
        btns.addWidget(delay_spin)
        table.setProperty("delay_spin", delay_spin)
        layout.addLayout(btns)
        return table, box

    # ---------- 表格行管理 ----------

    def _add_row(self, table, task_dict, kind):
        row = table.rowCount()
        table.insertRow(row)

        task = ProcessRow(
            task_dict["path"], kind,
            args=task_dict["args"],
            auto_restart=task_dict["auto_restart"],
            auto_start=task_dict["auto_start"],
        )

        status_item = QTableWidgetItem("● 已停止")
        status_item.setForeground(QColor("#80868b"))
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, COL_STATUS, status_item)

        path_item = QTableWidgetItem(task.path)
        path_item.setData(Qt.UserRole, task)
        path_item.setToolTip(task.path)
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, COL_PATH, path_item)

        args_item = QTableWidgetItem(task.args)
        args_item.setToolTip("roslaunch 填 arg:=值,py 填命令行参数")
        table.setItem(row, COL_ARGS, args_item)

        restart_item = QTableWidgetItem("")
        restart_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        restart_item.setCheckState(Qt.Checked if task.auto_restart else Qt.Unchecked)
        restart_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, COL_RESTART, restart_item)

        autostart_item = QTableWidgetItem("")
        autostart_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        autostart_item.setCheckState(Qt.Checked if task.auto_start else Qt.Unchecked)
        autostart_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, COL_AUTOSTART, autostart_item)

        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(4, 3, 4, 3)
        op_layout.setSpacing(6)
        start_btn = QPushButton("启动")
        start_btn.setObjectName("btnStart")
        stop_btn = QPushButton("停止")
        stop_btn.setObjectName("btnStop")
        start_btn.clicked.connect(lambda _, p=path_item: self.start_row(table, p))
        stop_btn.clicked.connect(lambda _, p=path_item: self.stop_row(table, p))
        op_layout.addWidget(start_btn)
        op_layout.addWidget(stop_btn)
        table.setCellWidget(row, COL_OPS, op_widget)
        if not self._loading:
            self.refresh_row_existence(table, path_item)
            self.save_config()

    def on_item_changed(self, kind, item):
        """参数 / 复选框改动时同步到 ProcessRow 并保存"""
        if self._loading:
            return
        table = self._table_of(kind)
        path_item = table.item(item.row(), COL_PATH)
        if not path_item:
            return
        task = path_item.data(Qt.UserRole)
        if item.column() == COL_ARGS:
            task.args = item.text().strip()
        elif item.column() == COL_RESTART:
            task.auto_restart = item.checkState() == Qt.Checked
        elif item.column() == COL_AUTOSTART:
            task.auto_start = item.checkState() == Qt.Checked
        else:
            return
        self.save_config()

    def _rows_of(self, table, selected_only=False):
        if selected_only:
            rows = sorted({i.row() for i in table.selectedIndexes()})
        else:
            rows = list(range(table.rowCount()))
        for r in rows:
            item = table.item(r, COL_PATH)
            if item:
                yield r, item.data(Qt.UserRole), item

    def _table_of(self, kind):
        return self.launch_table if kind == "launch" else self.py_table

    def _delay_ms(self, table):
        spin = table.property("delay_spin")
        return spin.value() * 1000 if spin else 0

    def on_delay_changed(self, value):
        """两个分组的延时框保持同步"""
        for kind in ("launch", "py"):
            spin = self._table_of(kind).property("delay_spin")
            if spin and spin.value() != value:
                spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(False)
        self.save_config()

    def refresh_row_existence(self, table, path_item, cache=None):
        """文件不存在时路径标红"""
        task = path_item.data(Qt.UserRole)
        if not task.is_running() and not task.exists(cache):
            path_item.setForeground(QColor("#ef5350"))
            path_item.setToolTip(task.path + "\n⚠ 文件不存在!")
        else:
            path_item.setForeground(QColor("#d7dae0"))
            path_item.setToolTip(task.path)

    def refresh_file_existence(self):
        self._file_exists_cache.clear()
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            for r, task, item in self._rows_of(table):
                self.refresh_row_existence(table, item, self._file_exists_cache)

    # ---------- 进程控制 ----------

    def start_row(self, table, path_item):
        if path_item.row() < 0:
            return  # 行已被移除
        task = path_item.data(Qt.UserRole)
        if task.is_running():
            self.log("【%s】已在运行中" % task.path)
            return
        if not task.exists():
            self.log("!! 文件不存在,无法启动: %s" % task.path)
            self.refresh_row_existence(table, path_item)
            return
        ros_setup = self.ros_setup_edit.text().strip()
        ws_setup = self.ws_setup_edit.text().strip()
        if not os.path.exists(ros_setup):
            QMessageBox.warning(self, "路径错误",
                                "ROS setup 文件不存在:\n%s" % ros_setup)
            return
        task.stop_requested = False
        task.restart_count = 0
        self.log(">>> 启动: %s %s" % (task.path, task.args))
        self._add_to_history(task.path)
        task.start(ros_setup, ws_setup, self.on_process_output, self.on_process_finished)
        if task.is_running():
            self._set_status(table, path_item, True)

    def stop_row(self, table, path_item):
        if path_item.row() < 0:
            return
        task = path_item.data(Qt.UserRole)
        task.stop()
        self.log("<<< 停止: %s" % task.path)
        self._set_status(table, path_item, False)

    def _set_status(self, table, path_item, running):
        row = path_item.row()
        if row < 0:
            return  # 行已被移除
        status_item = table.item(row, COL_STATUS)
        if running:
            status_item.setText("● 运行中")
            status_item.setForeground(QColor("#66bb6a"))
        else:
            status_item.setText("● 已停止")
            status_item.setForeground(QColor("#80868b"))

    def on_process_output(self, task, text):
        name = os.path.basename(task.path)
        for line in text.rstrip("\n").splitlines():
            self.log("[%s] %s" % (name, line))

    def on_process_finished(self, task):
        table = self._table_of(task.kind)
        path_item = None
        try:
            for r, t, item in self._rows_of(table):
                if t is task:
                    path_item = item
                    break
        except RuntimeError:
            return  # 窗口已销毁,忽略回调
        # 崩溃自动重启:非手动停止且勾选了自动重启
        if not task.stop_requested and task.auto_restart:
            if task.restart_count < MAX_RESTARTS:
                task.restart_count += 1
                self.log("!! 进程意外退出,2 秒后自动重启 (%d/%d): %s"
                         % (task.restart_count, MAX_RESTARTS, task.path))
                QTimer.singleShot(
                    2000, lambda: self._restart_task(table, path_item, task))
                return
            self.log("!! 进程反复崩溃,已达最大重启次数 %d,放弃: %s"
                     % (MAX_RESTARTS, task.path))
        self.log("=== 进程结束: %s" % task.path)
        if path_item is not None:
            self._set_status(table, path_item, False)

    def _restart_task(self, table, path_item, task):
        if path_item is None or task.stop_requested or task.is_running():
            return
        if path_item.row() < 0:
            return  # 行已被移除
        if not task.exists():
            self.log("!! 文件不存在,放弃自动重启: %s" % task.path)
            return
        ros_setup = self.ros_setup_edit.text().strip()
        ws_setup = self.ws_setup_edit.text().strip()
        task.start(ros_setup, ws_setup, self.on_process_output, self.on_process_finished)
        if task.is_running():
            self._set_status(table, path_item, True)

    # ---------- 按钮动作 ----------

    def add_file(self, kind):
        if kind == "launch":
            path, _ = QFileDialog.getOpenFileName(
                self, "选择 launch 文件", os.path.expanduser("~"),
                "Launch 文件 (*.launch);;所有文件 (*)")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择 Python 文件", os.path.expanduser("~"),
                "Python 文件 (*.py);;所有文件 (*)")
        if not path:
            return
        table = self._table_of(kind)
        for r, task, _ in self._rows_of(table):
            if task.path == path:
                QMessageBox.information(self, "已存在", "该文件已在列表中:\n%s" % path)
                return
        self._add_row(table, normalize_task(path), kind)
        self._add_to_history(path)

    def start_selected(self, kind):
        table = self._table_of(kind)
        for r, task, item in self._rows_of(table, selected_only=True):
            self.start_row(table, item)

    def stop_selected(self, kind):
        table = self._table_of(kind)
        for r, task, item in self._rows_of(table, selected_only=True):
            self.stop_row(table, item)

    def remove_selected(self, kind):
        table = self._table_of(kind)
        rows = sorted({i.row() for i in table.selectedIndexes()}, reverse=True)
        for r in rows:
            item = table.item(r, COL_PATH)
            if item:
                item.data(Qt.UserRole).stop()
            table.removeRow(r)
        if rows:
            self.save_config()

    def start_all(self, kind):
        """顺序延时启动:一个启动成功后再启动下一个"""
        table = self._table_of(kind)
        items = [item for r, task, item in self._rows_of(table)
                 if not task.is_running()]
        self._start_sequential(table, items, 0)

    def _start_sequential(self, table, items, index):
        if index >= len(items):
            return
        self.start_row(table, items[index])
        if index + 1 < len(items):
            QTimer.singleShot(
                self._delay_ms(table),
                lambda: self._start_sequential(table, items, index + 1))

    def stop_all(self, kind):
        table = self._table_of(kind)
        for r, task, item in self._rows_of(table):
            self.stop_row(table, item)

    def start_everything(self):
        """一键启动两个分组的全部任务:先 launch 后 py,统一延时"""
        table = self._table_of("launch")
        items = [(table, item) for r, task, item in self._rows_of(table)
                 if not task.is_running()]
        py_table = self._table_of("py")
        items += [(py_table, item) for r, task, item in self._rows_of(py_table)
                  if not task.is_running()]
        self._start_mixed_sequential(items, 0)

    def _start_mixed_sequential(self, items, index):
        if index >= len(items):
            return
        table, item = items[index]
        self.start_row(table, item)
        if index + 1 < len(items):
            QTimer.singleShot(
                self._delay_ms(table),
                lambda: self._start_mixed_sequential(items, index + 1))

    def stop_everything(self):
        self.stop_all("launch")
        self.stop_all("py")

    def auto_start_tasks(self):
        """打开软件后自动启动勾选了\"自启动\"的任务"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            items = [item for r, task, item in self._rows_of(table)
                     if task.auto_start and not task.is_running()]
            if items:
                self.log(">> 自动启动 %d 个任务(%s)"
                         % (len(items), "launch" if kind == "launch" else "py"))
                self._start_sequential(table, items, 0)

    # ---------- 配置 ----------

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = dict(DEFAULT_CONFIG)
                merged.update(cfg)
                return merged
        except (OSError, ValueError):
            # 配置文件损坏时备份一份,避免反复报错
            try:
                os.replace(CONFIG_FILE, CONFIG_FILE + ".bak")
            except OSError:
                pass
            return dict(DEFAULT_CONFIG)

    def save_config(self):
        if not hasattr(self, "launch_table") or self._loading:
            return
        self.config["ros_setup"] = self.ros_setup_edit.text().strip()
        self.config["ws_setup"] = self.ws_setup_edit.text().strip()
        spin = self.launch_table.property("delay_spin")
        if spin:
            self.config["start_delay"] = spin.value()
        self.config["launch_files"] = [
            t.to_dict() for _, t, _ in self._rows_of(self.launch_table)]
        self.config["py_files"] = [
            t.to_dict() for _, t, _ in self._rows_of(self.py_table)]
        try:
            # 原子写入:先写临时文件再替换,防止中途崩溃损坏配置
            tmp = CONFIG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            os.replace(tmp, CONFIG_FILE)
        except OSError as e:
            self.log("保存配置失败: %s" % e)

    # ---------- 日志 ----------

    def _init_log_file(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            name = "launcher-%s.log" % datetime.date.today().isoformat()
            self._log_file = open(os.path.join(LOG_DIR, name), "a", encoding="utf-8")
        except OSError:
            self._log_file = None

    def log(self, text):
        if hasattr(self, 'log_view') and self.log_view is not None:
            self.log_view.appendPlainText(text)
        if hasattr(self, '_status_label'):
            self._status_label.setText(text[-60:])
        if self._log_file:
            try:
                stamp = datetime.datetime.now().strftime("%H:%M:%S")
                self._log_file.write("[%s] %s\n" % (stamp, text))
                self._log_file.flush()
            except OSError:
                pass

    # ---------- 其它 ----------

    def browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", os.path.expanduser("~"), "所有文件 (*)")
        if path:
            line_edit.setText(path)
            self.save_config()

    def closeEvent(self, event):
        # 关闭窗口前停掉所有进程
        for kind in ("launch", "py"):
            for r, task, _ in self._rows_of(self._table_of(kind)):
                task.stop()
        self.save_config()
        if self._log_file:
            self._log_file.close()
        event.accept()

    def _validate_path(self, path):
        """验证路径安全性"""
        return self.security.validate_path(path)

    def _sanitize_command(self, command):
        """清理命令"""
        return self.security.sanitize_command(command)

    def _check_platform(self):
        """检查平台兼容性"""
        system = platform.system()
        if system not in ["Linux", "Windows", "Darwin"]:
            print(f"警告：未测试的平台 {system}")
        return system

    # ---------- 配置导入导出 ----------

    def import_config(self):
        """导入配置"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", os.path.expanduser("~"),
            "JSON 文件 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_config = json.load(f)
            # 验证配置格式
            if "ros_setup" not in new_config:
                QMessageBox.warning(self, "格式错误", "配置文件格式不正确")
                return
            # 备份当前配置
            self.export_config(backup=True)
            # 应用新配置
            self.config.update(new_config)
            self.ros_setup_edit.setText(self.config.get("ros_setup", ""))
            self.ws_setup_edit.setText(self.config.get("ws_setup", ""))
            self.save_config()
            QMessageBox.information(self, "导入成功", "配置已导入，请重启程序以完全应用")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def export_config(self, backup=False):
        """导出配置"""
        if backup:
            path = CONFIG_FILE + ".backup"
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "导出配置文件", os.path.expanduser("~/config_backup.json"),
                "JSON 文件 (*.json)")
            if not path:
                return
        try:
            self.save_config()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            if not backup:
                QMessageBox.information(self, "导出成功", f"配置已导出到:\n{path}")
            self.log("配置已导出到: %s" % path)
        except Exception as e:
            if not backup:
                QMessageBox.critical(self, "导出失败", str(e))

    # ---------- 远程更新 ----------

    def check_update(self):
        """检查更新"""
        self.log("正在检查更新...")
        
        # 读取更新配置
        config_path = os.path.join(BASE_DIR, "update_config.json")
        self.log("配置路径: %s" % config_path)
        self.log("文件存在: %s" % os.path.exists(config_path))
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    update_config = json.load(f)
                repo_owner = update_config.get("repo_owner", "")
                repo_name = update_config.get("repo_name", "")
                self.log("repo_owner: %s, repo_name: %s" % (repo_owner, repo_name))
            except Exception as e:
                self.log("读取配置失败: %s" % str(e))
                repo_owner = ""
                repo_name = ""
        else:
            repo_owner = ""
            repo_name = ""
        
        if not repo_owner or not repo_name:
            QMessageBox.information(self, "检查更新", 
                "未配置更新服务器。请编辑 update_config.json 文件。\n路径: %s" % config_path)
            return
        
        # 设置更新服务器
        self.updater.set_update_server(f"https://api.github.com/repos/{repo_owner}/{repo_name}")
        
        # 在后台线程中检查更新(不阻塞界面)
        self._run_async_ssh(
            lambda: self.updater.check_for_updates(),
            self._on_update_check_done
        )

    def _on_update_check_done(self, result):
        """更新检查完成回调(区分: 有更新/已最新/连接失败)"""
        try:
            # 后台线程异常包装格式
            if result is None:
                QMessageBox.warning(self, "检查更新", "无法连接到更新服务器(无响应)")
                return
            if isinstance(result, dict) and result.get("success") is False:
                QMessageBox.warning(self, "检查更新", f"无法连接到更新服务器:\n{result.get('error', '未知错误')}")
                return
            if not result.get("ok"):
                QMessageBox.warning(self, "检查更新", f"无法连接到更新服务器:\n{result.get('error', '未知错误')}")
                return
            
            data = result.get("data") or {}
            if "tag_name" in data:
                latest_version = data["tag_name"].lstrip("v")
                if self.updater.compare_versions(VERSION, latest_version) < 0:
                    reply = QMessageBox.question(
                        self, "发现新版本",
                        f"发现新版本 {latest_version}，当前版本 {VERSION}\n\n"
                        f"更新说明:\n{data.get('body', '无')}\n\n"
                        f"是否打开下载页面？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        import webbrowser
                        webbrowser.open(data.get("html_url", ""))
                else:
                    QMessageBox.information(self, "检查更新", f"当前已是最新版本 (v{VERSION})")
            else:
                QMessageBox.information(self, "检查更新", f"当前已是最新版本 (v{VERSION})")
        except Exception as e:
            QMessageBox.warning(self, "检查更新失败", f"检查更新出错:\n{str(e)}")

    def _download_update(self, release_info):
        """下载更新"""
        self.log("开始下载更新...")
        import webbrowser
        # 打开浏览器让用户手动下载
        if "assets" in release_info and release_info["assets"]:
            download_url = release_info["assets"][0].get("browser_download_url", "")
            if download_url:
                webbrowser.open(download_url)
        else:
            webbrowser.open(release_info.get("html_url", ""))

    # ---------- 系统监控 ----------

    def refresh_monitor(self):
        """刷新系统监控"""
        try:
            import psutil
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
            if hasattr(self, 'trend_chart'):
                self.trend_chart.add_data_point("cpu", cpu_percent)
            
            # 获取内存使用率
            mem = psutil.virtual_memory()
            self.mem_label.setText(f"内存: {mem.percent:.1f}%")
            if hasattr(self, 'trend_chart'):
                self.trend_chart.add_data_point("memory", mem.percent)
            
            # 获取运行中的进程
            running_tasks = []
            for kind in ("launch", "py"):
                for r, task, _ in self._rows_of(self._table_of(kind)):
                    if task.is_running():
                        name = os.path.basename(task.path)
                        pid = task.process.processId() if task.process else "N/A"
                        running_tasks.append(f"● {name} (PID: {pid})")
            
            if running_tasks:
                self.proc_list.setPlainText("\n".join(running_tasks))
            else:
                self.proc_list.setPlainText("无运行中的进程")
        except ImportError:
            self.cpu_label.setText("CPU: psutil未安装")
            self.mem_label.setText("内存: psutil未安装")
        except Exception as e:
            self.log(f"监控刷新失败: {e}")


    # ---------- 历史记录 ----------

    def _load_history(self):
        """加载历史记录到列表"""
        if not hasattr(self, 'history_list'):
            return
        self.history_list.clear()
        history = self.config.get("history", [])
        for item in history[-50:]:  # 最多显示50条
            self.history_list.addItem(item)

    def _add_to_history(self, path):
        """添加文件到历史记录"""
        if not path:
            return
        history = self.config.get("history", [])
        # 避免重复
        if path in history:
            history.remove(path)
        history.append(path)
        # 最多保留100条
        if len(history) > 100:
            history = history[-100:]
        self.config["history"] = history
        self.save_config()
        # 更新UI
        if hasattr(self, 'history_list'):
            self.history_list.clear()
            for item in history[-50:]:
                self.history_list.addItem(item)

    def _on_history_clicked(self, item):
        """双击历史记录项"""
        path = item.text()
        if not os.path.exists(path):
            QMessageBox.warning(self, "文件不存在", f"文件已不存在:\n{path}")
            return
        
        # 根据文件类型添加到对应的表格
        if path.endswith('.launch'):
            kind = "launch"
        elif path.endswith('.py'):
            kind = "py"
        else:
            # 询问用户
            reply = QMessageBox.question(self, "选择类型",
                "该文件应添加到哪个类别？",
                QMessageBox.Yes | QMessageBox.No)
            kind = "launch" if reply == QMessageBox.Yes else "py"
        
        table = self._table_of(kind)
        # 检查是否已存在
        for r, task, _ in self._rows_of(table):
            if task.path == path:
                QMessageBox.information(self, "已存在", "该文件已在列表中")
                return
        
        self._add_row(table, normalize_task(path), kind)
        self.log(f"从历史记录加载: {path}")

    def _clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(self, "确认清空",
            "确定要清空所有历史记录吗？",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config["history"] = []
            self.save_config()
            if hasattr(self, 'history_list'):
                self.history_list.clear()
            self.log("历史记录已清空")

    # ---------- 进度条 ----------

    def _update_progress(self, current, total):
        """更新进度条"""
        if hasattr(self, 'global_progress'):
            if total > 0:
                self.global_progress.setValue(int(current / total * 100))
                self.global_progress.show()
            else:
                self.global_progress.hide()

    # ---------- 场景管理 ----------

    def _load_scene_list(self):
        """加载场景列表"""
        if not hasattr(self, 'scene_list'):
            return
        self.scene_list.clear()
        scenes = self.scene_manager.get_scene_list()
        for scene in scenes:
            text = f"{scene['name']} ({scene['launch_count']}launch, {scene['py_count']}py)"
            self.scene_list.addItem(text)

    def _create_scene(self):
        """创建新场景"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "创建场景", "场景名称:")
        if ok and name:
            # 获取当前配置
            launch_files = [t.to_dict() for _, t, _ in self._rows_of(self.launch_table)]
            py_files = [t.to_dict() for _, t, _ in self._rows_of(self.py_table)]
            
            self.scene_manager.create_scene(
                name,
                launch_files=launch_files,
                py_files=py_files,
                ros_setup=self.ros_setup_edit.text(),
                ws_setup=self.ws_setup_edit.text(),
                start_delay=self.launch_table.property("delay_spin").value()
            )
            self._load_scene_list()
            self.log(f"创建场景: {name}")

    def _save_current_as_scene(self):
        """将当前配置保存为场景"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "保存场景", "场景名称:")
        if ok and name:
            launch_files = [t.to_dict() for _, t, _ in self._rows_of(self.launch_table)]
            py_files = [t.to_dict() for _, t, _ in self._rows_of(self.py_table)]
            
            self.scene_manager.create_scene(
                name,
                launch_files=launch_files,
                py_files=py_files,
                ros_setup=self.ros_setup_edit.text(),
                ws_setup=self.ws_setup_edit.text(),
                start_delay=self.launch_table.property("delay_spin").value()
            )
            self._load_scene_list()
            self.log(f"保存当前配置为场景: {name}")

    def _on_scene_clicked(self, item):
        """双击场景项"""
        scene_name = item.text().split(" (")[0]
        self._apply_scene_by_name(scene_name)

    def _apply_scene(self):
        """应用选中的场景"""
        current_item = self.scene_list.currentItem()
        if current_item:
            scene_name = current_item.text().split(" (")[0]
            self._apply_scene_by_name(scene_name)

    def _apply_scene_by_name(self, scene_name):
        """按名称应用场景"""
        config = self.scene_manager.apply_scene(scene_name)
        if not config:
            QMessageBox.warning(self, "错误", f"无法加载场景: {scene_name}")
            return
        
        # 清空当前列表
        self.launch_table.setRowCount(0)
        self.py_table.setRowCount(0)
        
        # 加载场景配置
        self.ros_setup_edit.setText(config.get("ros_setup", ""))
        self.ws_setup_edit.setText(config.get("ws_setup", ""))
        
        for entry in config.get("launch_files", []):
            self._add_row(self.launch_table, normalize_task(entry), "launch")
        
        for entry in config.get("py_files", []):
            self._add_row(self.py_table, normalize_task(entry), "py")
        
        delay_spin = self.launch_table.property("delay_spin")
        if delay_spin:
            delay_spin.setValue(config.get("start_delay", 3))
        
        self.config["current_scene"] = scene_name
        self.save_config()
        self.log(f"应用场景: {scene_name}")

    def _delete_scene(self):
        """删除场景"""
        current_item = self.scene_list.currentItem()
        if not current_item:
            return
        
        scene_name = current_item.text().split(" (")[0]
        reply = QMessageBox.question(self, "确认删除",
            f"确定要删除场景 '{scene_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.scene_manager.delete_scene(scene_name)
            self._load_scene_list()
            self.log(f"删除场景: {scene_name}")

    # ---------- 翻译工具 ----------

    def _translate_text(self):
        """翻译文本"""
        text = self.translator_input.text().strip()
        if text:
            translated = self.translator.translate(text)
            self.translator_output.setText(translated)

    def _copy_translation(self):
        """复制翻译结果"""
        text = self.translator_output.text()
        if text:
            QApplication.clipboard().setText(text)
            self.log("翻译结果已复制到剪贴板")

    def _toggle_translation(self):
        """切换翻译功能"""
        enabled = self.translation_enabled_cb.isChecked()
        self.config["translation_enabled"] = enabled
        self.save_config()
        self.log(f"自动翻译: {'启用' if enabled else '禁用'}")

    # ---------- 拖拽支持 ----------

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if os.path.isfile(path):
                self._add_file_by_path(path)

    def _add_file_by_path(self, path):
        """根据路径添加文件"""
        if path.endswith('.launch'):
            kind = "launch"
        elif path.endswith('.py'):
            kind = "py"
        else:
            return
        
        table = self._table_of(kind)
        for r, task, _ in self._rows_of(table):
            if task.path == path:
                return
        
        self._add_row(table, normalize_task(path), kind)
        self._add_to_history(path)
        self.log(f"通过拖拽添加: {path}")

    # ---------- 日志分离 ----------

    def on_process_output(self, task, text):
        """进程输出回调（带日志分离）"""
        name = os.path.basename(task.path)
        
        # 写入任务日志
        self.log_manager.write_log(name, text)
        
        # 写入合并日志
        for line in text.rstrip("\n").splitlines():
            log_line = "[%s] %s" % (name, line)
            
            # 自动翻译错误信息
            if self.config.get("translation_enabled", True):
                log_line = self.translator.translate(log_line)
            
            self.log(log_line)

    # ---------- ROS监控 ----------

    def _refresh_ros_master(self):
        """刷新ROS主节点状态(异步)"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self.ros_master_status.setText("状态: 查询中...")
        def on_done(result):
            if result["running"]:
                self.ros_master_status.setText("状态: 运行中 ✓")
                self.ros_master_status.setStyleSheet("color: #66bb6a; font-weight: bold;")
            else:
                self.ros_master_status.setText("状态: 未运行 ✗")
                self.ros_master_status.setStyleSheet("color: #ef5350; font-weight: bold;")
        self._run_async_ssh(lambda: self.ros_monitor.check_ros_master(), on_done)

    def _refresh_ros_nodes(self):
        """刷新ROS节点列表(异步)"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self.node_tree.clear()
        self.node_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", ""]))
        def on_done(result):
            self.node_tree.clear()
            if result["error"]:
                item = QTreeWidgetItem(["错误: " + result["error"]])
                self.node_tree.addTopLevelItem(item)
                return
            for node in result["nodes"]:
                item = QTreeWidgetItem([node, "存活", "", ""])
                self.node_tree.addTopLevelItem(item)
            self.log(f"刷新节点列表: {len(result['nodes'])} 个节点")
        self._run_async_ssh(lambda: self.ros_monitor.get_ros_nodes(), on_done)

    def _show_node_info(self):
        """显示节点信息"""
        current_item = self.node_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return
        
        node_name = current_item.text(0)
        result = self.ros_monitor.get_node_info(node_name)
        
        if result["error"]:
            QMessageBox.warning(self, "错误", f"获取节点信息失败:\n{result['error']}")
            return
        
        info = result["info"]
        msg = f"节点: {info['name']}\n"
        msg += f"PID: {info['pid'] or '未知'}\n"
        msg += f"\n发布者 ({len(info['publishers'])}):\n"
        for pub in info['publishers'][:5]:
            msg += f"  - {pub}\n"
        msg += f"\n订阅者 ({len(info['subscribers'])}):\n"
        for sub in info['subscribers'][:5]:
            msg += f"  - {sub}\n"
        msg += f"\n服务 ({len(info['services'])}):\n"
        for svc in info['services'][:5]:
            msg += f"  - {svc}\n"
        
        QMessageBox.information(self, "节点信息", msg)

    def _refresh_ros_topics(self):
        """刷新ROS Topic列表(异步)"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        self.topic_tree.clear()
        self.topic_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", ""]))
        def on_done(result):
            self.topic_tree.clear()
            if result["error"]:
                item = QTreeWidgetItem(["错误: " + result["error"]])
                self.topic_tree.addTopLevelItem(item)
                return
            for topic in result["topics"]:
                item = QTreeWidgetItem([topic, "", "", ""])
                self.topic_tree.addTopLevelItem(item)
        self._run_async_ssh(lambda: self.ros_monitor.get_ros_topics(), on_done)
        
        self.log(f"刷新Topic列表: {len(result['topics'])} 个话题")

    def _show_topic_info(self):
        """显示Topic信息"""
        current_item = self.topic_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个Topic")
            return
        
        topic_name = current_item.text(0)
        result = self.ros_monitor.get_topic_info(topic_name)
        
        if result["error"]:
            QMessageBox.warning(self, "错误", f"获取Topic信息失败:\n{result['error']}")
            return
        
        info = result["info"]
        msg = f"Topic: {info['name']}\n"
        msg += f"类型: {info['type'] or '未知'}\n"
        msg += f"\n发布者 ({len(info['publishers'])}):\n"
        for pub in info['publishers'][:5]:
            msg += f"  - {pub}\n"
        msg += f"\n订阅者 ({len(info['subscribers'])}):\n"
        for sub in info['subscribers'][:5]:
            msg += f"  - {sub}\n"
        
        QMessageBox.information(self, "Topic信息", msg)

    def _refresh_network(self):
        """刷新网络状态"""
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        
        master_uri = self.ros_monitor.get_ros_master_uri()
        master_status = self.ros_monitor.check_ros_master()
        
        info = f"ROS_MASTER_URI: {master_uri}\n"
        info += f"主节点状态: {'运行中' if master_status['running'] else '未运行'}\n"
        
        # 检查常用端口
        ports = [(11311, "ROS主节点"), (11312, "ROS节点")]
        for port, name in ports:
            is_open = self.ros_monitor.check_port_open("localhost", port)
            info += f"端口 {port} ({name}): {'开放' if is_open else '关闭'}\n"
        
        self.network_info.setPlainText(info)

    def _auto_refresh_ros_monitor(self):
        """自动刷新ROS监控(异步,防止定时器阻塞界面)"""
        # 更新ROS环境
        self.ros_monitor.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        
        def on_done(result):
            if result.get("running"):
                self.ros_master_status.setText("状态: 运行中 ✓")
                self.ros_master_status.setStyleSheet("color: #66bb6a; font-weight: bold;")
            else:
                self.ros_master_status.setText("状态: 未运行 ✗")
                self.ros_master_status.setStyleSheet("color: #ef5350; font-weight: bold;")
        
        self._run_async_ssh(
            lambda: self.ros_monitor.check_ros_master(),
            on_done
        )

    # ---------- 磁盘监控 ----------

    def _refresh_disk(self):
        """刷新磁盘信息(异步)"""
        self.disk_tree.clear()
        self.disk_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", "", "", ""]))
        def on_done(result):
            self.disk_tree.clear()
            if result["error"]:
                item = QTreeWidgetItem(["错误: " + result["error"]])
                self.disk_tree.addTopLevelItem(item)
                return
            for part in result["partitions"]:
                if "total" in part:
                    item = QTreeWidgetItem([
                        part["device"],
                        part["mountpoint"],
                        self.ros_monitor._format_size(part["total"]),
                        self.ros_monitor._format_size(part["used"]),
                        self.ros_monitor._format_size(part["free"]),
                        f"{part['percent']}%"
                    ])
                else:
                    item = QTreeWidgetItem([
                        part["device"],
                        part["mountpoint"],
                        part.get("size", "N/A"),
                        part.get("used", "N/A"),
                        part.get("available", "N/A"),
                        part.get("percent", "N/A")
                    ])
                self.disk_tree.addTopLevelItem(item)
        self._run_async_ssh(lambda: self.ros_monitor.get_disk_usage(), on_done)

    def _refresh_log_size(self):
        """刷新日志目录大小(异步)"""
        log_dir = os.path.join(BASE_DIR, "logs")
        self.log_size_label.setText("日志目录大小: 计算中...")
        def on_done(result):
            self.log_size_label.setText(f"日志目录大小: {result['size_human']}")
        self._run_async_ssh(
            lambda: self.ros_monitor.get_log_directory_size(log_dir),
            on_done
        )

    def _clean_old_logs(self):
        """清理旧日志"""
        reply = QMessageBox.question(self, "确认清理",
            "确定要清理30天前的日志文件吗？",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_manager.cleanup_old_logs(days=30)
            self._refresh_log_size()
            self.log("已清理旧日志文件")

    # ---------- 快捷键 ----------

    def _setup_hotkeys(self):
        """设置快捷键"""
        # F5 - 一键启动所有任务
        shortcut_start = QShortcut(QKeySequence("F5"), self)
        shortcut_start.activated.connect(self.start_everything)
        
        # F6 - 停止所有任务
        shortcut_stop = QShortcut(QKeySequence("F6"), self)
        shortcut_stop.activated.connect(self.stop_everything)
        
        # F7 - 启动选中的launch任务
        shortcut_start_launch = QShortcut(QKeySequence("F7"), self)
        shortcut_start_launch.activated.connect(lambda: self.start_selected("launch"))
        
        # F8 - 停止选中的launch任务
        shortcut_stop_launch = QShortcut(QKeySequence("F8"), self)
        shortcut_stop_launch.activated.connect(lambda: self.stop_selected("launch"))
        
        # Ctrl+L - 清空日志
        shortcut_clear_log = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_clear_log.activated.connect(self.log_view.clear)
        
        # Ctrl+S - 保存配置
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self.save_config)
        
        # Ctrl+R - 刷新监控
        shortcut_refresh = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut_refresh.activated.connect(self.refresh_monitor)

    # ---------- 多配置切换 ----------

    def _load_config_list(self):
        """加载配置列表"""
        if not hasattr(self, 'config_combo'):
            return
        
        self.config_combo.clear()
        
        # 获取所有配置文件
        config_dir = os.path.join(BASE_DIR, "configs")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        # 添加默认配置
        self.config_combo.addItem("默认配置")
        
        # 添加其他配置文件
        for f in os.listdir(config_dir):
            if f.endswith(".json"):
                config_name = f[:-5]  # 移除.json
                self.config_combo.addItem(config_name)
        
        # 设置当前配置
        current_config = self.config.get("current_config", "默认配置")
        index = self.config_combo.findText(current_config)
        if index >= 0:
            self.config_combo.setCurrentIndex(index)

    def _on_config_changed(self, config_name):
        """配置切换"""
        if config_name == "默认配置":
            return
        
        config_file = os.path.join(BASE_DIR, "configs", f"{config_name}.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
                
                # 应用新配置
                self.config.update(new_config)
                self.ros_setup_edit.setText(self.config.get("ros_setup", ""))
                self.ws_setup_edit.setText(self.config.get("ws_setup", ""))
                
                # 清空并重新加载任务列表
                self.launch_table.setRowCount(0)
                self.py_table.setRowCount(0)
                
                for entry in self.config.get("launch_files", []):
                    self._add_row(self.launch_table, normalize_task(entry), "launch")
                
                for entry in self.config.get("py_files", []):
                    self._add_row(self.py_table, normalize_task(entry), "py")
                
                delay_spin = self.launch_table.property("delay_spin")
                if delay_spin:
                    delay_spin.setValue(self.config.get("start_delay", 3))
                
                self.config["current_config"] = config_name
                self.save_config()
                self.log(f"切换到配置: {config_name}")
            except Exception as e:
                QMessageBox.warning(self, "切换失败", f"加载配置失败:\n{str(e)}")

    def _save_current_config(self):
        """保存当前配置"""
        from PyQt5.QtWidgets import QInputDialog
        
        # 获取当前配置名
        current_config = self.config.get("current_config", "默认配置")
        
        # 弹出输入框
        config_name, ok = QInputDialog.getText(
            self, "保存配置", 
            "配置名称:",
            text=current_config
        )
        
        if not ok or not config_name:
            return
        
        # 构建配置
        config_data = {
            "ros_setup": self.ros_setup_edit.text().strip(),
            "ws_setup": self.ws_setup_edit.text().strip(),
            "start_delay": self.launch_table.property("delay_spin").value(),
            "launch_files": [t.to_dict() for _, t, _ in self._rows_of(self.launch_table)],
            "py_files": [t.to_dict() for _, t, _ in self._rows_of(self.py_table)],
        }
        
        # 保存配置文件
        config_dir = os.path.join(BASE_DIR, "configs")
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, f"{config_name}.json")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.config["current_config"] = config_name
            self.save_config()
            
            # 刷新配置列表
            self._load_config_list()
            
            # 设置当前配置
            index = self.config_combo.findText(config_name)
            if index >= 0:
                self.config_combo.setCurrentIndex(index)
            
            self.log(f"配置已保存: {config_name}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存配置失败:\n{str(e)}")

    # ---------- 批量操作 ----------

    def _batch_select_all(self):
        """全选所有任务"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            table.selectAll()

    def _batch_deselect_all(self):
        """取消全选"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            table.clearSelection()

    def _batch_set_restart(self, enabled):
        """批量设置崩溃重启"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            for r, task, item in self._rows_of(table):
                task.auto_restart = enabled
                restart_item = table.item(r, COL_RESTART)
                if restart_item:
                    restart_item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
        
        self.save_config()
        self.log(f"批量{'启用' if enabled else '禁用'}崩溃重启")

    def _batch_set_autostart(self, enabled):
        """批量设置自启动"""
        for kind in ("launch", "py"):
            table = self._table_of(kind)
            for r, task, item in self._rows_of(table):
                task.auto_start = enabled
                autostart_item = table.item(r, COL_AUTOSTART)
                if autostart_item:
                    autostart_item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
        
        self.save_config()
        self.log(f"批量{'启用' if enabled else '禁用'}自启动")

    # ---------- 任务调度 ----------

    def _add_schedule(self):
        """添加定时任务"""
        from PyQt5.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(self, "添加定时任务", "任务名称:")
        if not ok or not name:
            return
        
        # 选择任务类型
        task_type, ok = QInputDialog.getItem(self, "选择任务类型", "类型:", 
                                             ["launch", "py"], 0, False)
        if not ok:
            return
        
        # 选择任务路径
        if task_type == "launch":
            path, _ = QFileDialog.getOpenFileName(self, "选择launch文件", 
                                                  os.path.expanduser("~"), 
                                                  "Launch文件 (*.launch)")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择Python文件", 
                                                  os.path.expanduser("~"), 
                                                  "Python文件 (*.py)")
        
        if not path:
            return
        
        # 选择调度类型
        schedule_type, ok = QInputDialog.getItem(self, "选择调度类型", "类型:",
                                                 ["once", "repeat"], 0, False)
        if not ok:
            return
        
        interval = None
        if schedule_type == "repeat":
            interval, ok = QInputDialog.getInt(self, "设置间隔", "间隔秒数:", 3600, 60, 86400)
            if not ok:
                return
        
        self.task_scheduler.add_schedule(
            name, task_type, path, schedule_type, interval=interval
        )
        self._refresh_schedules()
        self.log(f"添加定时任务: {name}")

    def _refresh_schedules(self):
        """刷新调度列表"""
        self.schedule_tree.clear()
        schedules = self.task_scheduler.get_schedule_list()
        
        for schedule in schedules:
            item = QTreeWidgetItem([
                schedule["name"],
                schedule["task_type"],
                schedule["task_path"],
                "启用" if schedule["enabled"] else "禁用",
                schedule.get("next_run", "未计划")
            ])
            self.schedule_tree.addTopLevelItem(item)

    # ---------- 仿真控制 ----------

    def _pause_simulation(self):
        """暂停仿真(异步)"""
        self._status_label.setText("暂停仿真中...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("仿真已暂停")
            else:
                QMessageBox.warning(self, "错误", f"暂停仿真失败:\n{result['error']}")
        self._run_async_ssh(lambda: self.sim_controller.pause_simulation(), on_done)

    def _unpause_simulation(self):
        """继续仿真(异步)"""
        self._status_label.setText("继续仿真中...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("仿真已继续")
            else:
                QMessageBox.warning(self, "错误", f"继续仿真失败:\n{result['error']}")
        self._run_async_ssh(lambda: self.sim_controller.unpause_simulation(), on_done)

    def _reset_simulation(self):
        """重置仿真(异步)"""
        self._status_label.setText("重置仿真中...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log("仿真已重置")
            else:
                QMessageBox.warning(self, "错误", f"重置仿真失败:\n{result['error']}")
        self._run_async_ssh(lambda: self.sim_controller.reset_simulation(), on_done)

    def _spawn_model(self):
        """生成模型(异步)"""
        from PyQt5.QtWidgets import QInputDialog
        
        model_name, ok = QInputDialog.getText(self, "生成模型", "模型名称:")
        if not ok or not model_name:
            return
        
        self._status_label.setText(f"生成模型 {model_name} ...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"模型已生成: {model_name}")
            else:
                QMessageBox.warning(self, "错误", f"生成模型失败:\n{result['error']}")
        self._run_async_ssh(lambda: self.sim_controller.spawn_model(model_name), on_done)

    def _delete_model(self):
        """删除模型(异步)"""
        from PyQt5.QtWidgets import QInputDialog
        
        model_name, ok = QInputDialog.getText(self, "删除模型", "模型名称:")
        if not ok or not model_name:
            return
        
        self._status_label.setText(f"删除模型 {model_name} ...")
        self.sim_controller.set_ros_env(
            self.ros_setup_edit.text().strip(),
            self.ws_setup_edit.text().strip()
        )
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"模型已删除: {model_name}")
            else:
                QMessageBox.warning(self, "错误", f"删除模型失败:\n{result['error']}")
        self._run_async_ssh(lambda: self.sim_controller.delete_model(model_name), on_done)

    # ---------- 日志分析 ----------

    def _analyze_all_logs(self):
        """分析所有日志"""
        analysis = self.log_analyzer.analyze_all_logs()
        
        if "error" in analysis:
            QMessageBox.warning(self, "错误", f"分析日志失败:\n{analysis['error']}")
            return
        
        report = self.log_analyzer.generate_report(analysis)
        self.analysis_result.setPlainText(report)
        self.log(f"日志分析完成: {analysis['total_errors']}个错误, {analysis['total_warnings']}个警告")

    def _search_errors(self):
        """搜索错误"""
        from PyQt5.QtWidgets import QInputDialog
        
        keyword, ok = QInputDialog.getText(self, "搜索错误", "关键词:")
        if not ok:
            return
        
        results = self.log_analyzer.search_errors(keyword=keyword)
        
        report = f"搜索结果: {len(results)}条匹配\n\n"
        for r in results[:50]:  # 最多显示50条
            report += f"[{r['file']}] 行{r['line']}: {r['content'][:100]}\n"
        
        self.analysis_result.setPlainText(report)

    def _export_report(self):
        """导出分析报告"""
        path, _ = QFileDialog.getSaveFileName(self, "导出报告",
                                              os.path.expanduser("~/log_report.txt"),
                                              "文本文件 (*.txt)")
        if not path:
            return
        
        analysis = self.log_analyzer.analyze_all_logs()
        report = self.log_analyzer.generate_report(analysis, path)
        self.log(f"报告已导出: {path}")

    # ---------- 多机协同 ----------

    def _get_selected_machine(self):
        """获取当前选中的机器"""
        current_item = self.machine_tree.currentItem()
        if not current_item:
            return None
        return current_item.text(0)

    def _on_machine_selected(self):
        """机器选择变化"""
        machine_name = self._get_selected_machine()
        if machine_name:
            self._refresh_remote_nodes()
            self._refresh_remote_topics()
            self._refresh_robot_status()

    def _add_machine(self):
        """添加机器"""
        from PyQt5.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(self, "添加机器", "机器名称:")
        if not ok or not name:
            return
        
        hostname, ok = QInputDialog.getText(self, "添加机器", "主机名/IP:")
        if not ok or not hostname:
            return
        
        username, ok = QInputDialog.getText(self, "添加机器", "用户名:")
        if not ok or not username:
            return
        
        port, ok = QInputDialog.getInt(self, "添加机器", "SSH端口:", 22, 1, 65535)
        if not ok:
            return
        
        password, ok = QInputDialog.getText(self, "添加机器", "密码(可选，用于免密登录):", 
                                           QLineEdit.EchoMode.Password)
        if not ok:
            password = None
        
        ros_setup, ok = QInputDialog.getText(
            self, "添加机器", "ROS环境配置:",
            text="source ~/.bashrc"
        )
        if not ok:
            ros_setup = "source ~/.bashrc"
        
        self.multi_machine.add_machine(name, hostname, username, port, password, ros_setup)
        self._refresh_machines()
        self.log(f"添加机器: {name}")

    def _remove_machine(self):
        """删除选中的机器"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        reply = QMessageBox.question(
            self, "删除机器",
            f"确定要删除机器 [{machine_name}] 吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        result = self.multi_machine.remove_machine(machine_name)
        if result:
            self._refresh_machines()
            self.log(f"删除机器: {machine_name}")
        else:
            QMessageBox.warning(self, "错误", f"删除机器失败: {machine_name}")

    def _run_async_ssh(self, fn, on_done=None):
        """在后台线程执行SSH操作,避免卡住界面;完成后回到主线程回调"""
        import threading
        def worker():
            try:
                result = fn()
            except Exception as e:
                result = {"success": False, "error": str(e)}
            if on_done:
                QTimer.singleShot(0, lambda: on_done(result))
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _test_machine_connection(self):
        """测试机器连接(异步,不卡界面)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        # 状态栏提示
        self._status_label.setText(f"正在测试连接 {machine_name} ...")
        
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                QMessageBox.information(self, "成功", f"连接 {machine_name} 成功!")
                self._refresh_machines()
            else:
                QMessageBox.warning(self, "失败", f"连接 {machine_name} 失败:\n{result['error']}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.test_connection(machine_name),
            on_done
        )

    def _setup_machine_key(self):
        """设置SSH密钥"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        result = self.multi_machine.setup_ssh_key(machine_name)
        if result["success"]:
            QMessageBox.information(self, "成功", result.get("message", "密钥设置成功"))
        else:
            QMessageBox.warning(self, "失败", f"密钥设置失败:\n{result['error']}")

    def _refresh_machines(self):
        """刷新机器列表"""
        self.machine_tree.clear()
        machines = self.multi_machine.get_machine_list()
        
        for machine in machines:
            if not isinstance(machine, dict):
                continue
            item = QTreeWidgetItem([
                machine.get("name", "未知"),
                machine.get("hostname", ""),
                machine.get("username", ""),
                str(machine.get("port", 22)),
                "已连接" if machine.get("connected", False) else "未连接"
            ])
            self.machine_tree.addTopLevelItem(item)

    # ---------- ROS远程控制 ----------

    def _remote_start_master(self):
        """远程启动roscore(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        self._status_label.setText(f"正在 {machine_name} 启动roscore ...")
        
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"在 {machine_name} 启动roscore")
            else:
                QMessageBox.warning(self, "错误", f"启动roscore失败:\n{result['error']}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.start_ros_master(machine_name),
            on_done
        )

    def _remote_stop_master(self):
        """远程停止roscore(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        self._status_label.setText(f"正在停止 {machine_name} roscore ...")
        
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"在 {machine_name} 停止roscore")
            else:
                QMessageBox.warning(self, "错误", f"停止roscore失败:\n{result['error']}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.stop_ros_master(machine_name),
            on_done
        )

    def _remote_start_launch(self):
        """远程启动launch文件(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        launch_file, ok = QInputDialog.getText(self, "启动launch文件", 
                                               "launch文件名(如: turtlebot3_slam):")
        if not ok or not launch_file:
            return
        
        self._status_label.setText(f"正在 {machine_name} 启动launch ...")
        
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"在 {machine_name} 启动launch: {launch_file}")
            else:
                QMessageBox.warning(self, "错误", f"启动launch失败:\n{result['error']}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.start_launch_file_background(machine_name, launch_file),
            on_done
        )

    def _remote_stop_launch(self):
        """远程停止launch(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        self._status_label.setText(f"正在停止 {machine_name} launch ...")
        
        def on_done(result):
            self._status_label.setText("就绪")
            if result["success"]:
                self.log(f"在 {machine_name} 停止launch")
            else:
                QMessageBox.warning(self, "错误", f"停止launch失败:\n{result['error']}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.stop_launch_process(machine_name),
            on_done
        )

    def _refresh_remote_nodes(self):
        """刷新远程节点列表(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        self.remote_nodes_list.clear()
        self.remote_nodes_list.addItem("加载中...")
        
        def on_done(result):
            self.remote_nodes_list.clear()
            if result.get("error"):
                self.remote_nodes_list.addItem(f"错误: {result['error']}")
            else:
                for node in result["nodes"]:
                    self.remote_nodes_list.addItem(node)
        
        self._run_async_ssh(
            lambda: self.multi_machine.get_ros_nodes(machine_name),
            on_done
        )

    def _refresh_remote_topics(self):
        """刷新远程话题列表(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        self.remote_topics_list.clear()
        self.remote_topics_list.addItem("加载中...")
        
        def on_done(result):
            self.remote_topics_list.clear()
            if result.get("error"):
                self.remote_topics_list.addItem(f"错误: {result['error']}")
            else:
                for topic in result["topics"]:
                    self.remote_topics_list.addItem(topic)
        
        self._run_async_ssh(
            lambda: self.multi_machine.get_ros_topics(machine_name),
            on_done
        )

    def _refresh_robot_status(self):
        """刷新机器人状态(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        self.remote_cpu_label.setText("CPU: 查询中...")
        
        def on_done(status):
            self.remote_cpu_label.setText(f"CPU: {status.get('cpu', '--')}")
            self.remote_mem_label.setText(f"内存: {status.get('memory', '--')}")
            self.remote_disk_label.setText(f"磁盘: {status.get('disk', '--')}")
            self.remote_uptime_label.setText(f"运行时间: {status.get('uptime', '--')}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.get_robot_status(machine_name),
            on_done
        )

    def _execute_remote_command(self):
        """执行远程命令(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        command = self.custom_cmd_edit.text().strip()
        if not command:
            QMessageBox.information(self, "提示", "请输入要执行的命令")
            return
        
        self.cmd_output.setPlainText("执行中...")
        self._status_label.setText(f"正在远程执行: {command}")
        
        def on_done(result):
            self._status_label.setText("就绪")
            self.cmd_output.clear()
            if result["success"]:
                self.cmd_output.setPlainText(result.get("output", ""))
            else:
                self.cmd_output.setPlainText(f"错误:\n{result.get('error', '未知错误')}")
        
        self._run_async_ssh(
            lambda: self.multi_machine.execute_remote_command(machine_name, command),
            on_done
        )

    # ---------- 插件管理 ----------

    def _discover_plugins(self):
        """发现插件"""
        plugins = self.plugin_manager.discover_plugins()
        self.log(f"发现 {len(plugins)} 个插件")

    def _load_plugin(self):
        """加载插件"""
        from PyQt5.QtWidgets import QInputDialog
        
        plugins = self.plugin_manager.discover_plugins()
        if not plugins:
            QMessageBox.information(self, "提示", "未发现可用插件")
            return
        
        plugin_names = [p["name"] for p in plugins]
        name, ok = QInputDialog.getItem(self, "加载插件", "选择插件:", plugin_names, 0, False)
        if not ok:
            return
        
        result = self.plugin_manager.load_plugin(name)
        if result["success"]:
            self.log(f"插件已加载: {name}")
        else:
            QMessageBox.warning(self, "错误", f"加载插件失败:\n{result['error']}")

    def _refresh_plugins(self):
        """刷新插件列表"""
        self.plugin_tree.clear()
        plugins = self.plugin_manager.get_loaded_plugins()
        
        for plugin in plugins:
            info = plugin.get("info", {})
            item = QTreeWidgetItem([
                plugin["name"],
                "已加载",
                info.get("description", ""),
                info.get("version", "")
            ])
            self.plugin_tree.addTopLevelItem(item)

    # ---------- 远程文件浏览器 ----------

    def _refresh_remote_files(self):
        """刷新远程文件列表(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        current_path = self.remote_path_edit.text().strip()
        if not current_path:
            current_path = "~"
            self.remote_path_edit.setText(current_path)
        
        self.remote_dir_tree.clear()
        self.remote_dir_tree.addTopLevelItem(QTreeWidgetItem(["加载中...", "", "", ""]))
        
        def on_done(result):
            self.remote_dir_tree.clear()
            
            if not result["success"]:
                self.remote_dir_tree.addTopLevelItem(QTreeWidgetItem(["连接失败...", "", "", ""]))
                return
            
            output = result.get("output", "")
            if output.startswith("ERROR:"):
                self.remote_dir_tree.addTopLevelItem(QTreeWidgetItem([output, "", "", ""]))
                return
            
            # 解析ls -la输出
            lines = output.split("\n")
            for line in lines:
                if not line.strip() or line.startswith("total"):
                    continue
                
                # 解析文件信息
                parts = line.split(None, 7)
                if len(parts) < 9:
                    continue
                
                permissions = parts[0]
                size = parts[4]
                date = f"{parts[5]} {parts[6]}"
                name = parts[8]
                
                # 跳过.和..
                if name in (".", ".."):
                    continue
                
                # 判断类型
                if permissions.startswith("d"):
                    file_type = "目录"
                    name_display = f"📁 {name}"
                elif permissions.startswith("l"):
                    file_type = "链接"
                    name_display = f"🔗 {name}"
                elif name.endswith(".launch"):
                    file_type = "Launch文件"
                    name_display = f"🚀 {name}"
                elif name.endswith(".py"):
                    file_type = "Python文件"
                    name_display = f"🐍 {name}"
                elif name.endswith((".yaml", ".yml")):
                    file_type = "YAML文件"
                    name_display = f"📄 {name}"
                elif name.endswith((".bag",)):
                    file_type = "Bag文件"
                    name_display = f"📦 {name}"
                else:
                    file_type = "文件"
                    name_display = f"📄 {name}"
                
                item = QTreeWidgetItem([name_display, size, file_type, date])
                item.setData(0, Qt.UserRole, name)  # 存储原始文件名
                self.remote_dir_tree.addTopLevelItem(item)
        
        # 获取文件列表
        cmd = f"ls -la {current_path} 2>/dev/null || echo 'ERROR:目录不存在'"
        self._run_async_ssh(
            lambda: self.multi_machine._run_ssh_command(machine_name, cmd),
            on_done
        )

    def _remote_go_home(self):
        """回到主目录"""
        self.remote_path_edit.setText("~")
        self._refresh_remote_files()

    def _remote_go_back(self):
        """返回上级目录"""
        current_path = self.remote_path_edit.text().strip()
        if current_path and current_path != "/":
            parent = os.path.dirname(current_path)
            if not parent:
                parent = "/"
            self.remote_path_edit.setText(parent)
            self._refresh_remote_files()

    def _remote_goto_path(self):
        """跳转到指定路径"""
        self._refresh_remote_files()

    def _remote_file_double_clicked(self, item, column):
        """双击文件/目录"""
        if not item:
            return
        
        name = item.data(0, Qt.UserRole)
        current_path = self.remote_path_edit.text().strip()
        
        # 构建完整路径
        if current_path.endswith("/"):
            full_path = current_path + name
        else:
            full_path = current_path + "/" + name
        
        # 判断是否为目录
        file_type = item.text(2)
        if file_type == "目录" or file_type == "链接":
            self.remote_path_edit.setText(full_path)
            self._refresh_remote_files()
        elif name.endswith((".launch", ".py")):
            # 双击launch或py文件，询问是否运行
            reply = QMessageBox.question(
                self, "运行文件",
                f"是否要运行 {name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._remote_run_file(full_path)

    def _remote_file_selected(self):
        """文件选中变化"""
        current_item = self.remote_dir_tree.currentItem()
        if current_item:
            name = current_item.data(0, Qt.UserRole)
            current_path = self.remote_path_edit.text().strip()
            if current_path.endswith("/"):
                full_path = current_path + name
            else:
                full_path = current_path + "/" + name
            self.search_edit.setText(full_path)

    def _remote_run_selected_file(self):
        """运行选中的文件"""
        current_item = self.remote_dir_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个文件")
            return
        
        name = current_item.data(0, Qt.UserRole)
        current_path = self.remote_path_edit.text().strip()
        
        if current_path.endswith("/"):
            full_path = current_path + name
        else:
            full_path = current_path + "/" + name
        
        self._remote_run_file(full_path)

    def _remote_run_file(self, file_path):
        """运行远程文件"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            QMessageBox.information(self, "提示", "请先选择一台机器")
            return
        
        if file_path.endswith(".launch"):
            # 获取launch包名和文件名
            # /path/to/package/launch/file.launch -> package file.launch
            path_parts = file_path.split("/")
            
            # 找到launch目录
            launch_idx = -1
            for i, part in enumerate(path_parts):
                if part == "launch":
                    launch_idx = i
                    break
            
            if launch_idx > 0 and launch_idx < len(path_parts) - 1:
                package = path_parts[launch_idx - 1]
                launch_file = path_parts[-1]
                launch_name = f"{package} {launch_file}"
            else:
                launch_name = file_path
            
            reply = QMessageBox.question(
                self, "启动launch文件",
                f"是否要启动 {launch_name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._status_label.setText(f"正在 {machine_name} 启动launch ...")
                def on_done_launch(result):
                    self._status_label.setText("就绪")
                    if result["success"]:
                        self.log(f"在 {machine_name} 启动launch: {launch_name}")
                    else:
                        QMessageBox.warning(self, "错误", f"启动launch失败:\n{result['error']}")
                self._run_async_ssh(
                    lambda: self.multi_machine.start_launch_file_background(machine_name, launch_name),
                    on_done_launch
                )
        
        elif file_path.endswith(".py"):
            reply = QMessageBox.question(
                self, "运行Python文件",
                f"是否要运行 {file_path}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                cmd = f"python3 {file_path} &"
                self._status_label.setText(f"正在 {machine_name} 运行 {file_path} ...")
                def on_done_py(result):
                    self._status_label.setText("就绪")
                    if result["success"]:
                        self.log(f"在 {machine_name} 运行: {file_path}")
                    else:
                        QMessageBox.warning(self, "错误", f"运行Python文件失败:\n{result['error']}")
                self._run_async_ssh(
                    lambda: self.multi_machine._run_ssh_command(machine_name, cmd, timeout=5),
                    on_done_py
                )

    def _remote_add_to_launch(self):
        """添加到launch列表"""
        current_item = self.remote_dir_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个文件")
            return
        
        name = current_item.data(0, Qt.UserRole)
        file_type = current_item.text(2)
        
        if not name.endswith(".launch"):
            QMessageBox.information(self, "提示", "只能添加.launch文件")
            return
        
        current_path = self.remote_path_edit.text().strip()
        if current_path.endswith("/"):
            full_path = current_path + name
        else:
            full_path = current_path + "/" + name
        
        # 获取远程机器信息
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        # 添加到表格
        task_dict = {
            "path": full_path,
            "args": f"--remote {machine_name}",
            "auto_restart": False,
            "auto_start": False,
        }
        
        self._add_row(self.launch_table, task_dict, "launch")
        self.save_config()
        self.log(f"添加远程launch: {full_path}")

    def _remote_add_to_py(self):
        """添加到py列表"""
        current_item = self.remote_dir_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个文件")
            return
        
        name = current_item.data(0, Qt.UserRole)
        file_type = current_item.text(2)
        
        if not name.endswith(".py"):
            QMessageBox.information(self, "提示", "只能添加.py文件")
            return
        
        current_path = self.remote_path_edit.text().strip()
        if current_path.endswith("/"):
            full_path = current_path + name
        else:
            full_path = current_path + "/" + name
        
        # 获取远程机器信息
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        # 添加到表格
        task_dict = {
            "path": full_path,
            "args": f"--remote {machine_name}",
            "auto_restart": False,
            "auto_start": False,
        }
        
        self._add_row(self.py_table, task_dict, "py")
        self.save_config()
        self.log(f"添加远程py: {full_path}")

    def _remote_search_files(self):
        """搜索远程文件(异步)"""
        machine_name = self._get_selected_machine()
        if not machine_name:
            return
        
        keyword = self.search_edit.text().strip()
        if not keyword:
            QMessageBox.information(self, "提示", "请输入搜索关键词")
            return
        
        current_path = self.remote_path_edit.text().strip()
        
        self.remote_dir_tree.clear()
        self.remote_dir_tree.addTopLevelItem(QTreeWidgetItem(["搜索中...", "", "", ""]))
        
        def on_done(result):
            self.remote_dir_tree.clear()
            if result["success"] and result["output"]:
                files = result["output"].split("\n")
                for file_path in files:
                    if not file_path.strip():
                        continue
                    
                    name = os.path.basename(file_path)
                    dir_path = os.path.dirname(file_path)
                    
                    if name.endswith(".launch"):
                        file_type = "Launch文件"
                        name_display = f"🚀 {name}"
                    elif name.endswith(".py"):
                        file_type = "Python文件"
                        name_display = f"🐍 {name}"
                    else:
                        file_type = "文件"
                        name_display = f"📄 {name}"
                    
                    item = QTreeWidgetItem([name_display, "", file_type, dir_path])
                    item.setData(0, Qt.UserRole, file_path)
                    self.remote_dir_tree.addTopLevelItem(item)
            else:
                self.remote_dir_tree.addTopLevelItem(QTreeWidgetItem(["未找到匹配文件", "", "", ""]))
        
        # 搜索文件
        cmd = f"find {current_path} -name '*{keyword}*' -type f 2>/dev/null | head -50"
        self._run_async_ssh(
            lambda: self.multi_machine._run_ssh_command(machine_name, cmd, timeout=10),
            on_done
        )


def _global_excepthook(exc_type, exc_value, exc_tb):
    """全局异常兜底:记录崩溃日志,避免静默闪退"""
    try:
        crash_log = os.path.join(LOG_DIR, "crash.log")
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write("\n[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exc_type.__name__))
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    traceback.print_exception(exc_type, exc_value, exc_tb)


def main():
    sys.excepthook = _global_excepthook
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
