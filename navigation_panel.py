#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键导航模块
- 发送目标点到move_base(actionlib)
- 航点巡航
- 停止导航/取消目标
"""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QLineEdit, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QMessageBox,
                             QHeaderView)
from ros_widget_base import ROSWidget


class NavigationWidget(ROSWidget):
    """一键导航"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.waypoints = []  # [(name, x, y, theta)]
        self._build_source_cmd()
        self._init_ui()


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
        self.wp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
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

        # 导航状态提示
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8be9fd; padding: 4px;")
        layout.addWidget(self.status_label)


    def _send_goal(self):
        x = self.x_spin.value()
        y = self.y_spin.value()
        theta = self.theta_spin.value()
        self._go_to(x, y, theta)

    def _go_to(self, x, y, theta, name="目标"):
        import math
        theta_rad = math.radians(theta)
        # 使用python脚本通过actionlib发送(后台线程执行,不阻塞界面)
        # frame_id自动选择: 优先map,不存在则回退odom,均不存在时给出明确错误
        script = f'''
import math, rospy, actionlib, tf2_ros
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
rospy.init_node("gui_nav_goal", anonymous=True)
client = actionlib.SimpleActionClient("move_base", MoveBaseAction)
if not client.wait_for_server(rospy.Duration(5)):
    print("ERROR:move_base服务5秒内无响应,请确认导航环境已启动(如 navigation.launch 或 Gazebo导航)")
    exit(1)
def frame_available(fid):
    try:
        buf = tf2_ros.Buffer()
        tf2_ros.TransformListener(buf)
        for i in range(6):
            try:
                buf.lookup_transform(fid, "base_link", rospy.Time(0), rospy.Duration(0.2))
                return True
            except Exception:
                rospy.sleep(0.1)
    except Exception:
        pass
    return False
frame_id = "map" if frame_available("map") else "odom"
if not frame_available(frame_id):
    print("ERROR:frame_id map/odom均不存在,请确认定位与导航环境已启动(amcl/map_server),frame_id不匹配会导致导航无响应")
    exit(1)
goal = MoveBaseGoal()
goal.target_pose.header.frame_id = frame_id
goal.target_pose.pose.position.x = {x}
goal.target_pose.pose.position.y = {y}
goal.target_pose.pose.orientation.z = math.sin({theta_rad}/2)
goal.target_pose.pose.orientation.w = math.cos({theta_rad}/2)
client.send_goal(goal)
client.wait_for_result(rospy.Duration(30))
state = client.get_state()
if state == 3:
    print("SUCCESS")
elif state == 4:
    print("ERROR:move_base拒绝目标,目标点可能不可达或存在障碍物")
else:
    print("ERROR:导航失败,state=%d,请检查move_base与代价地图状态" % state)
'''
        self.status_label.setText(f"⏳ 导航中: 目标[{name}] ({x}, {y}) ...")

        def on_done(result):
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            if "SUCCESS" in stdout:
                self.status_label.setText(f"✅ 已到达目标点 [{name}]")
                self.log_if_any(f"导航到[{name}]成功")
                QMessageBox.information(self, "导航", f"到达目标点 [{name}]")
            elif "ERROR" in stdout:
                msg = stdout.split("ERROR:", 1)[1].strip()
                self.status_label.setText(f"❌ 导航失败: {msg}")
                self.log_if_any(f"导航到[{name}]失败: {msg}")
                QMessageBox.warning(self, "导航失败", msg)
            else:
                self.status_label.setText(f"❌ 导航失败: {name}")
                self.log_if_any(f"导航到[{name}]失败: {stdout}{stderr[:100]}")
                QMessageBox.warning(self, "导航", f"导航失败:\n{stdout}{stderr[:200]}")

        self._run_bg(lambda: self._run_cmd(f"python3 -c '{script}'", timeout=40),
                     on_done)

    def _cancel_goal(self):
        self._run_bg(lambda: self._run_cmd(
            "rostopic pub -1 /move_base/cancel actionlib_msgs/GoalID '{}'"))
        self.log_if_any("已取消导航目标")

    def _clear_costmap(self):
        self._run_bg(lambda: self._run_cmd("rosservice call /move_base/clear_costmaps"))
        self.log_if_any("已清除代价地图")

    def _nav_status(self):
        self.status_label.setText("⏳ 查询导航状态...")

        def on_done(result):
            stdout = result.get("stdout", "")
            text = stdout or "move_base未运行或无状态消息"
            self.status_label.setText("📡 " + text.replace("\n", " ")[:50])
            QMessageBox.information(self, "导航状态", text)

        self._run_bg(lambda: self._run_cmd(
            "rostopic echo -n1 /move_base/status 2>/dev/null | grep -E 'status|text' | head -4",
            timeout=6), on_done)

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
