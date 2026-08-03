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
_optional_modules = [
    ("robot_control", "RobotControlWidget"), ("navigation_panel", "NavigationWidget"),
    ("sensor_panel", "SensorPanelWidget"), ("camera_view", "CameraViewWidget"),
    ("topic_table", "TopicTableWidget"), ("bag_manager", "BagManagerWidget"),
    ("alarm_system", "AlarmSystemWidget"), ("serial_debug", "SerialDebugWidget"),
    ("web_remote", "WebRemoteWidget"),
]
for _mod, _cls in _optional_modules:
    try:
        globals()[_cls] = getattr(__import__(_mod), _cls)
    except Exception as e:
        print(f"加载{_mod}失败: {e}")
        globals()[_cls] = None

from constants import (BASE_DIR, CONFIG_FILE, LOG_DIR, VERSION, DEFAULT_CONFIG,
                      MAX_RESTARTS, COL_STATUS, COL_PATH, COL_ARGS, COL_RESTART,
                      COL_AUTOSTART, COL_OPS, normalize_task)
from functools import lru_cache
from mixins_tasks import TasksMixin
from mixins_config import ConfigMixin
from mixins_monitor import MonitorMixin
from mixins_simulation import SimulationMixin
from mixins_remote import RemoteMixin
from PyQt6.QtCore import Qt, QProcess, QTimer
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QHeaderView, QSpinBox, QTabWidget, QProgressBar,
    QListWidget, QListWidgetItem, QDockWidget, QSplitter, QTreeWidget,
    QTreeWidgetItem, QHeaderView as QTreeHeaderView, QComboBox,
    QStackedWidget,
)


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
QLabel { color: #f8fafc; }
QLabel[dim="true"] { color: #94a3b8; }
QMainWindow, QWidget {
    background-color: #282a36;
    color: #f8f8f2;
    font-size: 13px;
}
/* ---- 卡片 ---- */
QGroupBox {
    background-color: #2f3241;
    border: 1px solid #44475a;
    border-radius: 14px;
    margin-top: 16px;
    padding-top: 12px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 2px 12px;
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
    border-radius: 8px;
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
    border-radius: 10px;
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
    border-radius: 6px;
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
    border-radius: 10px;
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
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
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
    border-radius: 8px;
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
    border-radius: 6px;
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
    border-radius: 5px;
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


from process_row import ProcessRow

class MainWindow(QMainWindow, TasksMixin, ConfigMixin, MonitorMixin, SimulationMixin, RemoteMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROS 一键启动器 v%s" % VERSION)
        self.resize(1400, 900)
        self._load_style()
        self.config = self.load_config()
        # 自动探测工作空间:ws_setup为空时自动填充常见路径(输入框会显示,用户保存后持久化)
        if not self.config.get("ws_setup"):
            detected = ProcessRow._auto_detect_ws()
            if detected:
                self.config["ws_setup"] = detected
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

        # 液态玻璃背景层
        try:
            from glass_background import GlassBackground
            self.glass_bg = GlassBackground(central)
            self.glass_bg.setGeometry(central.rect())
            self.glass_bg.lower()
            central._glass_bg = self.glass_bg  # 防GC
        except Exception as e:
            self.glass_bg = None
            print("玻璃背景加载失败:", e)

        # ---- 全局操作 (轻量级,立即初始化) ----
        from ui_anim import add_press_effect
        global_row = QHBoxLayout()
        start_everything = QPushButton("▶  一键启动所有任务")
        start_everything.setObjectName("btnGlobalStart")
        start_everything.setMinimumHeight(46)
        start_everything.clicked.connect(self.start_everything)
        add_press_effect(start_everything)
        stop_everything = QPushButton("■  停止所有任务")
        stop_everything.setObjectName("btnGlobalStop")
        stop_everything.setMinimumHeight(46)
        stop_everything.clicked.connect(self.stop_everything)
        add_press_effect(stop_everything)
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
        self.task_splitter = QSplitter(Qt.Orientation.Horizontal)
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
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
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
        """延迟初始化重量级组件(防重入)"""
        if getattr(self, "_heavy_initialized", False):
            return
        self._heavy_initialized = True
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

        # Gazebo环境启动
        gazebo_group = QGroupBox("🚀 Gazebo环境")
        gazebo_layout = QVBoxLayout(gazebo_group)

        env_btn_row = QHBoxLayout()
        self.start_gazebo_btn = QPushButton("▶ 启动Gazebo空世界")
        self.start_gazebo_btn.clicked.connect(self._start_gazebo)
        env_btn_row.addWidget(self.start_gazebo_btn)

        stop_gazebo_btn = QPushButton("⏹ 停止Gazebo")
        stop_gazebo_btn.clicked.connect(self._stop_gazebo)
        env_btn_row.addWidget(stop_gazebo_btn)

        gazebo_status_btn = QPushButton("📡 状态")
        gazebo_status_btn.clicked.connect(self._refresh_gazebo_status)
        env_btn_row.addWidget(gazebo_status_btn)

        env_btn_row.addStretch()
        gazebo_layout.addLayout(env_btn_row)

        # 仿真场景预设
        scene_row = QHBoxLayout()
        scene_row.addWidget(QLabel("仿真场景:"))
        self.scene_combo = QComboBox()
        self.scene_combo.setMinimumWidth(280)
        scene_row.addWidget(self.scene_combo, 1)
        start_scene_btn = QPushButton("▶ 启动场景")
        start_scene_btn.clicked.connect(self._start_scene)
        scene_row.addWidget(start_scene_btn)
        gazebo_layout.addLayout(scene_row)

        # 状态显示
        self.gazebo_status_label = QLabel("Gazebo: 未运行")
        self.gazebo_status_label.setStyleSheet("color: #6272a4; padding: 2px;")
        gazebo_layout.addWidget(self.gazebo_status_label)

        sim_layout.addWidget(gazebo_group)

        # Gazebo仿真控制(暂停/继续/重置)
        sim_group = QGroupBox("🎛 仿真控制")
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

        sim_inner_layout.addStretch()
        sim_layout.addWidget(sim_group)

        # 模型管理
        model_group = QGroupBox("🤖 模型管理")
        model_layout = QVBoxLayout(model_group)

        model_btn_layout = QHBoxLayout()
        spawn_model_btn = QPushButton("加载URDF模型")
        spawn_model_btn.clicked.connect(self._load_urdf_model)
        model_btn_layout.addWidget(spawn_model_btn)

        spawn_sdf_btn = QPushButton("加载SDF模型")
        spawn_sdf_btn.clicked.connect(self._load_sdf_model)
        model_btn_layout.addWidget(spawn_sdf_btn)

        delete_model_btn = QPushButton("删除模型")
        delete_model_btn.clicked.connect(self._delete_model)
        model_btn_layout.addWidget(delete_model_btn)

        refresh_models_btn = QPushButton("刷新模型列表")
        refresh_models_btn.clicked.connect(self._refresh_gazebo_models)
        model_btn_layout.addWidget(refresh_models_btn)

        model_btn_layout.addStretch()
        model_layout.addLayout(model_btn_layout)

        self.model_list = QListWidget()
        model_layout.addWidget(self.model_list)

        sim_layout.addWidget(model_group)
        sim_layout.addStretch()

        add_page(sim_widget, "🎮 仿真控制")

        # 加载仿真场景列表
        try:
            scenes = self.sim_controller.get_common_scenes()
            for s in scenes:
                self.scene_combo.addItem(f"{s['pkg']}/{s['file']}")
        except Exception:
            pass

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

        # 导航栏点击切换页面(页面不可见时暂停其定时器,避免后台消耗CPU)
        def _on_nav_changed(index):
            # 暂停所有页面的定时器
            for i in range(self.content_stack.count()):
                w = self.content_stack.widget(i)
                pause = getattr(w, "pause_timers", None)
                if pause:
                    if i != index:
                        try:
                            pause()
                        except Exception:
                            pass
            self.content_stack.setCurrentIndex(index)
            # 恢复当前页面的定时器
            w = self.content_stack.widget(index)
            resume = getattr(w, "resume_timers", None)
            if resume:
                try:
                    resume()
                except Exception:
                    pass

        self.nav_list.currentRowChanged.connect(_on_nav_changed)
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


    # ---------- 表格行管理 ----------


    # ---------- 进程控制 ----------


    # ---------- 按钮动作 ----------


    # ---------- 配置 ----------


    # ---------- 日志 ----------


    # ---------- 其它 ----------


    # ---------- 配置导入导出 ----------


    # ---------- 远程更新 ----------


    # ---------- 系统监控 ----------


    # ---------- 历史记录 ----------


    # ---------- 进度条 ----------


    # ---------- 场景管理 ----------


    # ---------- 翻译工具 ----------


    # ---------- 拖拽支持 ----------


    # ---------- 日志分离 ----------


    # ---------- ROS监控 ----------


    # ---------- 磁盘监控 ----------


    # ---------- 快捷键 ----------


    # ---------- 多配置切换 ----------


    # ---------- 批量操作 ----------


    # ---------- 任务调度 ----------


    # ---------- 仿真控制 ----------


    # ---------- 日志分析 ----------


    # ---------- 多机协同 ----------


    # ---------- ROS远程控制 ----------


    # ---------- 插件管理 ----------


    # ---------- 远程文件浏览器 ----------


def _global_excepthook(exc_type, exc_value, exc_tb):
    """全局异常兜底:记录崩溃日志,避免静默闪退"""
    try:
        crash_log = os.path.join(LOG_DIR, "crash.log")
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write("\n[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exc_type.__name__))
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        # fallback 到 /tmp 或当前目录
        try:
            fallback = "/tmp/ros_launcher_crash.log" if os.path.isdir("/tmp") else "crash.log"
            with open(fallback, "a", encoding="utf-8") as f:
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
