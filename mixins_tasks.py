#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mixins_tasks.py - TasksMixin
由launcher_gui.py自动拆分生成,功能不变
"""
from process_row import ProcessRow
import os
import platform
import json
import datetime
import webbrowser
import subprocess
import traceback
from constants import (BASE_DIR, CONFIG_FILE, LOG_DIR, VERSION, DEFAULT_CONFIG,
                      MAX_RESTARTS, COL_STATUS, COL_PATH, COL_ARGS, COL_RESTART,
                      COL_AUTOSTART, COL_OPS, normalize_task)
from PyQt5.QtCore import Qt, QProcess, QTimer, QRectF
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog,
                             QGroupBox, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QAbstractItemView, QMessageBox,
                             QHeaderView, QSpinBox, QListWidgetItem, QComboBox,
                             QShortcut, QInputDialog, QTreeWidgetItem)


class TasksMixin:
    """MainWindow功能mixin"""

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
        up_btn = QPushButton("↑ 上移")
        up_btn.clicked.connect(lambda: self.move_task(kind, -1))
        down_btn = QPushButton("↓ 下移")
        down_btn.clicked.connect(lambda: self.move_task(kind, 1))
        for b in (add_btn, start_btn, stop_btn, remove_btn, start_all, stop_all,
                  up_btn, down_btn):
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

    def move_task(self, kind, direction):
        """上移/下移选中任务,调整启动顺序
        direction: -1上移, 1下移
        """
        table = self._table_of(kind)
        rows = sorted({i.row() for i in table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "提示", "请先选择要移动的任务")
            return
        
        # 逐行移动(选择多行时整体移动)
        if direction == -1:  # 上移
            for r in rows:
                if r == 0:
                    continue
                self._swap_rows(table, r, r - 1)
        else:  # 下移
            for r in reversed(rows):
                if r >= table.rowCount() - 1:
                    continue
                self._swap_rows(table, r, r + 1)
        
        self.save_config()
        # 保持选中
        table.clearSelection()
        for r in rows:
            item = table.item(r, COL_PATH)
            if item:
                item.setSelected(True)

    def _swap_rows(self, table, r1, r2):
        """交换表格两行(所有列+操作widget)"""
        if r1 < 0 or r2 < 0 or r1 >= table.rowCount() or r2 >= table.rowCount():
            return
        
        for col in range(6):
            item1 = table.takeItem(r1, col)
            item2 = table.takeItem(r2, col)
            if item1:
                table.setItem(r2, col, item1)
            if item2:
                table.setItem(r1, col, item2)
        
        # 交换操作列的widget
        w1 = table.cellWidget(r1, COL_OPS)
        w2 = table.cellWidget(r2, COL_OPS)
        if w1 and w2:
            table.setCellWidget(r1, COL_OPS, w2)
            table.setCellWidget(r2, COL_OPS, w1)

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
        # QProcess需要短暂时间进入Running状态,延迟检查避免状态列不更新
        QTimer.singleShot(400, lambda: self._confirm_started(table, path_item, task))

    def _confirm_started(self, table, path_item, task):
        """延迟确认任务已启动,更新状态列"""
        try:
            if task.is_running():
                self._set_status(table, path_item, True)
            else:
                self.log("!! 进程未能启动: %s" % task.path)
                self._set_status(table, path_item, False)
        except RuntimeError:
            pass  # 窗口已销毁

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
