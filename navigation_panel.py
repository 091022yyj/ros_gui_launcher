#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键导航模块
- 发送目标点到move_base(actionlib)
- 航点巡航
- 停止导航/取消目标
"""
import os
import subprocess
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QLineEdit, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QMessageBox,
                             QHeaderView)


class NavigationWidget(QWidget):
    """一键导航"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.waypoints = []  # [(name, x, y, theta)]
        self._build_source_cmd()
        self._init_ui()

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

    def _run_cmd(self, cmd, timeout=15):
        full = f"{self.source_cmd} && {cmd}" if self.source_cmd else cmd
        try:
            result = subprocess.run(["bash", "-c", full], capture_output=True,
                                    text=True, timeout=timeout)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令超时", 1
        except Exception as e:
            return "", str(e), 1

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 目标点设置
        goal_group = QGroupBox("发送目标点 (move_base)")
        goal_layout = QHBoxLayout(goal_group)
        goal_layout.addWidget(QLabel("X:"))
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-20, 20)
        self.x_spin.setDecimals(2)
        self.x_spin.setValue(2.0)
        goal_layout.addWidget(self.x_spin)
        goal_layout.addWidget(QLabel("Y:"))
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-20, 20)
        self.y_spin.setDecimals(2)
        goal_layout.addWidget(self.y_spin)
        goal_layout.addWidget(QLabel("朝向°:"))
        self.theta_spin = QDoubleSpinBox()
        self.theta_spin.setRange(-180, 180)
        self.theta_spin.setDecimals(1)
        goal_layout.addWidget(self.theta_spin)

        self.send_goal_btn = QPushButton("🚀 发送目标")
        self.send_goal_btn.clicked.connect(self._send_goal)
        goal_layout.addWidget(self.send_goal_btn)
        layout.addWidget(goal_group)

        # 操作按钮
        op_group = QGroupBox("导航操作")
        op_layout = QHBoxLayout(op_group)
        cancel_btn = QPushButton("✋ 取消目标")
        cancel_btn.clicked.connect(self._cancel_goal)
        op_layout.addWidget(cancel_btn)
        clear_costmap_btn = QPushButton("🧹 清除代价地图")
        clear_costmap_btn.clicked.connect(self._clear_costmap)
        op_layout.addWidget(clear_costmap_btn)
        status_btn = QPushButton("📡 导航状态")
        status_btn.clicked.connect(self._nav_status)
        op_layout.addWidget(status_btn)
        layout.addWidget(op_group)

        # 航点管理
        wp_group = QGroupBox("航点巡航")
        wp_layout = QVBoxLayout(wp_group)
        wp_input = QHBoxLayout()
        self.wp_name_edit = QLineEdit()
        self.wp_name_edit.setPlaceholderText("航点名(如: 充电桩)")
        wp_input.addWidget(self.wp_name_edit)
        add_wp_btn = QPushButton("+ 添加当前坐标为航点")
        add_wp_btn.clicked.connect(self._add_waypoint)
        wp_input.addWidget(add_wp_btn)
        wp_layout.addLayout(wp_input)

        self.wp_table = QTableWidget(0, 5)
        self.wp_table.setHorizontalHeaderLabels(["航点名", "X", "Y", "朝向°", "操作"])
        self.wp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.wp_table.setColumnWidth(4, 160)
        self.wp_table.verticalHeader().setVisible(False)
        wp_layout.addWidget(self.wp_table)

        wp_btn_row = QHBoxLayout()
        cruise_btn = QPushButton("▶ 巡航所有航点")
        cruise_btn.clicked.connect(self._cruise_all)
        wp_btn_row.addWidget(cruise_btn)
        remove_wp_btn = QPushButton("🗑 删除选中航点")
        remove_wp_btn.clicked.connect(self._remove_waypoint)
        wp_btn_row.addWidget(remove_wp_btn)
        wp_btn_row.addStretch()
        wp_layout.addLayout(wp_btn_row)
        layout.addWidget(wp_group)

        layout.addStretch()

    def _send_goal(self):
        x = self.x_spin.value()
        y = self.y_spin.value()
        theta = self.theta_spin.value()
        self._go_to(x, y, theta)

    def _go_to(self, x, y, theta, name="目标"):
        import math
        theta_rad = math.radians(theta)
        # 用roslaunch的move_base goal? 用actionlib或rostopic
        # 简单方式: 使用python脚本通过actionlib发送
        script = f'''
import math, rospy, actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
rospy.init_node("gui_nav_goal")
client = actionlib.SimpleActionClient("move_base", MoveBaseAction)
if not client.wait_for_server(rospy.Duration(5)):
    print("ERROR:move_base服务不可用")
    exit(1)
goal = MoveBaseGoal()
goal.target_pose.header.frame_id = "map"
goal.target_pose.pose.position.x = {x}
goal.target_pose.pose.position.y = {y}
goal.target_pose.pose.orientation.z = math.sin({theta_rad}/2)
goal.target_pose.pose.orientation.w = math.cos({theta_rad}/2)
client.send_goal(goal)
client.wait_for_result(rospy.Duration(30))
print("SUCCESS" if client.get_state() == 3 else "FAILED")
'''
        stdout, stderr, code = self._run_cmd(f"python3 -c '{script}'", timeout=40)
        if "SUCCESS" in stdout:
            self.log_if_any(f"导航到[{name}]成功")
            QMessageBox.information(self, "导航", f"到达目标点 [{name}]")
        elif "ERROR" in stdout:
            QMessageBox.warning(self, "导航失败", "move_base服务不可用,请确认导航已启动")
        else:
            self.log_if_any(f"导航到[{name}]失败: {stdout}{stderr[:100]}")
            QMessageBox.warning(self, "导航", f"导航失败:\n{stdout}{stderr[:200]}")

    def _cancel_goal(self):
        cmd = "rostopic pub -1 /move_base/cancel actionlib_msgs/GoalID '{}'"
        self._run_cmd(cmd)
        self.log_if_any("已取消导航目标")

    def _clear_costmap(self):
        self._run_cmd("rosservice call /move_base/clear_costmaps")
        self.log_if_any("已清除代价地图")

    def _nav_status(self):
        stdout, stderr, code = self._run_cmd(
            "rostopic echo -n1 /move_base/status 2>/dev/null | grep -E 'status|text' | head -4",
            timeout=8)
        if stdout:
            QMessageBox.information(self, "导航状态", stdout or "状态未知")
        else:
            QMessageBox.information(self, "导航状态", "move_base未运行或无状态消息")

    def _add_waypoint(self):
        name = self.wp_name_edit.text().strip()
        if not name:
            name = f"航点{len(self.waypoints)+1}"
        self.waypoints.append((name, self.x_spin.value(), self.y_spin.value(),
                               self.theta_spin.value()))
        self._refresh_wp_table()

    def _refresh_wp_table(self):
        self.wp_table.setRowCount(0)
        for i, (name, x, y, theta) in enumerate(self.waypoints):
            self.wp_table.insertRow(i)
            self.wp_table.setItem(i, 0, QTableWidgetItem(name))
            self.wp_table.setItem(i, 1, QTableWidgetItem(f"{x:.2f}"))
            self.wp_table.setItem(i, 2, QTableWidgetItem(f"{y:.2f}"))
            self.wp_table.setItem(i, 3, QTableWidgetItem(f"{theta:.1f}"))
            go_btn = QPushButton("去这里")
            go_btn.clicked.connect(lambda _, idx=i: self._go_to(
                self.waypoints[idx][1], self.waypoints[idx][2],
                self.waypoints[idx][3], self.waypoints[idx][0]))
            self.wp_table.setCellWidget(i, 4, go_btn)

    def _remove_waypoint(self):
        row = self.wp_table.currentRow()
        if row >= 0 and row < len(self.waypoints):
            del self.waypoints[row]
            self._refresh_wp_table()

    def _cruise_all(self):
        if not self.waypoints:
            QMessageBox.information(self, "巡航", "请先添加航点")
            return
        for name, x, y, theta in self.waypoints:
            self._go_to(x, y, theta, name)

    def log_if_any(self, text):
        pass
