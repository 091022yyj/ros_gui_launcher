#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mixins_remote.py - RemoteMixin
由launcher_gui.py自动拆分生成,功能不变
"""
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
from PyQt6.QtCore import Qt, QProcess, QTimer, QRectF
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog,
                             QGroupBox, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QAbstractItemView, QMessageBox,
                             QHeaderView, QSpinBox, QListWidgetItem, QComboBox,
                            QInputDialog, QTreeWidgetItem)


class RemoteMixin:
    """MainWindow功能mixin"""

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
        from PyQt6.QtWidgets import QInputDialog

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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        result = self.multi_machine.remove_machine(machine_name)
        if result:
            self._refresh_machines()
            self.log(f"删除机器: {machine_name}")
        else:
            QMessageBox.warning(self, "错误", f"删除机器失败: {machine_name}")

    def _run_async(self, fn, on_done=None):
        """后台线程执行耗时操作,避免卡住界面;完成后回到主线程回调(线程安全)"""
        from async_helper import run_async
        run_async(fn, on_done)

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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
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

        self._run_async(
            lambda: self.multi_machine.execute_remote_command(machine_name, command),
            on_done
        )

    def _discover_plugins(self):
        """发现插件"""
        plugins = self.plugin_manager.discover_plugins()
        self.log(f"发现 {len(plugins)} 个插件")

    def _load_plugin(self):
        """加载插件"""
        from PyQt6.QtWidgets import QInputDialog

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
                item.setData(0, Qt.ItemDataRole.UserRole, name)  # 存储原始文件名
                self.remote_dir_tree.addTopLevelItem(item)

        # 获取文件列表
        cmd = f"ls -la {current_path} 2>/dev/null || echo 'ERROR:目录不存在'"
        self._run_async(
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

        name = item.data(0, Qt.ItemDataRole.UserRole)
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._remote_run_file(full_path)

    def _remote_file_selected(self):
        """文件选中变化"""
        current_item = self.remote_dir_tree.currentItem()
        if current_item:
            name = current_item.data(0, Qt.ItemDataRole.UserRole)
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

        name = current_item.data(0, Qt.ItemDataRole.UserRole)
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._status_label.setText(f"正在 {machine_name} 启动launch ...")
                def on_done_launch(result):
                    self._status_label.setText("就绪")
                    if result["success"]:
                        self.log(f"在 {machine_name} 启动launch: {launch_name}")
                    else:
                        QMessageBox.warning(self, "错误", f"启动launch失败:\n{result['error']}")
                self._run_async(
                    lambda: self.multi_machine.start_launch_file_background(machine_name, launch_name),
                    on_done_launch
                )

        elif file_path.endswith(".py"):
            reply = QMessageBox.question(
                self, "运行Python文件",
                f"是否要运行 {file_path}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                cmd = f"python3 {file_path} &"
                self._status_label.setText(f"正在 {machine_name} 运行 {file_path} ...")
                def on_done_py(result):
                    self._status_label.setText("就绪")
                    if result["success"]:
                        self.log(f"在 {machine_name} 运行: {file_path}")
                    else:
                        QMessageBox.warning(self, "错误", f"运行Python文件失败:\n{result['error']}")
                self._run_async(
                    lambda: self.multi_machine._run_ssh_command(machine_name, cmd, timeout=5),
                    on_done_py
                )

    def _remote_add_to_launch(self):
        """添加到launch列表"""
        current_item = self.remote_dir_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个文件")
            return

        name = current_item.data(0, Qt.ItemDataRole.UserRole)
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

        name = current_item.data(0, Qt.ItemDataRole.UserRole)
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
                    item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                    self.remote_dir_tree.addTopLevelItem(item)
            else:
                self.remote_dir_tree.addTopLevelItem(QTreeWidgetItem(["未找到匹配文件", "", "", ""]))

        # 搜索文件
        cmd = f"find {current_path} -name '*{keyword}*' -type f 2>/dev/null | head -50"
        self._run_async(
            lambda: self.multi_machine._run_ssh_command(machine_name, cmd, timeout=10),
            on_done
        )
