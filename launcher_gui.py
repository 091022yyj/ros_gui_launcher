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

from security import SecurityManager
from functools import lru_cache
from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QHeaderView, QSpinBox,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
VERSION = "1.2.0"

DEFAULT_CONFIG = {
    "ros_setup": "/opt/ros/noetic/setup.bash",
    "ws_setup": "",  # 例如 ~/catkin_ws/devel/setup.bash
    "start_delay": 3,  # 顺序启动时每个任务之间的延时(秒)
    "launch_files": [],
    "py_files": [],
}

MAX_RESTARTS = 3  # 崩溃自动重启的最大次数

# 表格列
COL_STATUS, COL_PATH, COL_ARGS, COL_RESTART, COL_AUTOSTART, COL_OPS = range(6)


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
        self.resize(1000, 700)
        self._load_style()
        self.config = self.load_config()
        self._loading = False
        self._log_file = None
        self._file_exists_cache = {}
        self.security = SecurityManager()
        self._check_platform()

        central = QWidget()
        self.setCentralWidget(central)
        self._main_layout = QVBoxLayout(central)

        # ---- 全局操作 (轻量级,立即初始化) ----
        global_row = QHBoxLayout()
        start_everything = QPushButton("▶ 一键启动所有任务")
        start_everything.clicked.connect(self.start_everything)
        stop_everything = QPushButton("■ 停止所有任务")
        stop_everything.clicked.connect(self.stop_everything)
        global_row.addWidget(start_everything)
        global_row.addWidget(stop_everything)
        global_row.addStretch(1)
        self._main_layout.addLayout(global_row)

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

        # ---- launch 文件 (轻量级,立即初始化) ----
        self.launch_table, launch_box = self._make_task_group(
            "Launch 文件 (roslaunch)", "launch")
        self._main_layout.addWidget(launch_box)

        # ---- py 文件 (轻量级,立即初始化) ----
        self.py_table, py_box = self._make_task_group(
            "Python 文件 (python3)", "py")
        self._main_layout.addWidget(py_box)

        # ---- 日志 (延迟初始化,重量级组件) ----
        self._log_box_placeholder = QWidget()
        self._main_layout.addWidget(self._log_box_placeholder)

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
        """加载样式表"""
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(style_path):
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())

    def _init_heavy_components(self):
        """延迟初始化重量级组件"""
        # 延迟初始化日志视图
        self._init_log_file()
        log_box = QGroupBox("运行日志 (同步保存到 logs/ 目录)")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        log_layout.addWidget(self.log_view)
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_view.clear)
        log_layout.addWidget(clear_btn)

        # 替换占位符
        idx = self._main_layout.indexOf(self._log_box_placeholder)
        if idx >= 0:
            self._main_layout.removeWidget(self._log_box_placeholder)
            self._log_box_placeholder.deleteLater()
            self._main_layout.insertWidget(idx, log_box)

        # 延迟刷新文件存在性
        self.refresh_file_existence()

        # 打开软件后自动启动勾选了的任务(延时错开)
        QTimer.singleShot(1000, self.auto_start_tasks)

    # ---------- UI 构建 ----------

    def _make_task_group(self, title, kind):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["状态", "文件路径", "启动参数", "崩溃重启", "自启动", "操作"])
        table.horizontalHeader().setSectionResizeMode(COL_PATH, QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
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
        status_item.setForeground(Qt.gray)
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
        table.setItem(row, COL_RESTART, restart_item)

        autostart_item = QTableWidgetItem("")
        autostart_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        autostart_item.setCheckState(Qt.Checked if task.auto_start else Qt.Unchecked)
        table.setItem(row, COL_AUTOSTART, autostart_item)

        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(2, 2, 2, 2)
        start_btn = QPushButton("启动")
        stop_btn = QPushButton("停止")
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
            path_item.setForeground(Qt.red)
            path_item.setToolTip(task.path + "\n⚠ 文件不存在!")
        else:
            path_item.setForeground(Qt.black)
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
            status_item.setForeground(Qt.darkGreen)
        else:
            status_item.setText("● 已停止")
            status_item.setForeground(Qt.gray)

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


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
