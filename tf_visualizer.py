#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TF图形化查看器
- 图形化显示TF坐标系关系
- 支持交互式查看
"""
import os
import subprocess
import re
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainter, QPainterPath
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QMessageBox, QInputDialog,
    QGroupBox, QSplitter, QTextEdit, QTreeWidget, QTreeWidgetItem
)
from ros_widget_base import ROSWidget


class TFFrame(QGraphicsEllipseItem):
    """TF坐标系图形项"""
    
    def __init__(self, name, x, y, parent=None):
        super().__init__(-30, -30, 60, 60, parent)
        self.name = name
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#4a90d9")))
        self.setPen(QPen(QColor("#2d5a8a"), 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        # 添加标签
        self.label = QGraphicsTextItem(name, self)
        self.label.setPos(-20, 35)
        self.label.setDefaultTextColor(QColor("#ffffff"))
        self.label.setFont(QFont("Arial", 10))
        
        # 存储连接关系
        self.connections = []
    
    def hoverEnterEvent(self, event):
        """鼠标悬停进入"""
        self.setBrush(QBrush(QColor("#6ab0ff")))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """鼠标悬停离开"""
        self.setBrush(QBrush(QColor("#4a90d9")))
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标点击"""
        super().mousePressEvent(event)


class TFConnection(QGraphicsLineItem):
    """TF连接线"""
    
    def __init__(self, parent_frame, child_frame, parent=None):
        super().__init__(parent)
        self.parent_frame = parent_frame
        self.child_frame = child_frame
        self.update_position()
        
        self.setPen(QPen(QColor("#8ab4f8"), 2, Qt.SolidLine))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
    
    def update_position(self):
        """更新位置"""
        if self.parent_frame and self.child_frame:
            self.setLine(
                self.parent_frame.pos().x(),
                self.parent_frame.pos().y(),
                self.child_frame.pos().x(),
                self.child_frame.pos().y()
            )
    
    def paint(self, painter, option, widget=None):
        """绘制连接线"""
        if self.parent_frame and self.child_frame:
            # 绘制箭头
            painter.setPen(self.pen())
            painter.drawLine(self.line())
            
            # 绘制箭头头部
            end_point = self.child_frame.pos()
            start_point = self.parent_frame.pos()
            
            direction = end_point - start_point
            if direction.manhattanLength() > 0:
                direction = direction / direction.manhattanLength() * 10
                
                # 箭头位置
                arrow_pos = end_point - direction * 3
                arrow_size = 8
                
                # 计算箭头方向
                angle = direction.y() / direction.x() if direction.x() != 0 else 0
                
                painter.setBrush(QBrush(QColor("#8ab4f8")))
                painter.drawEllipse(arrow_pos, arrow_size, arrow_size)


class TFGraphicsView(QGraphicsView):
    """TF图形视图"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 存储坐标系
        self.frames = {}
        self.connections = []
    
    def clear_scene(self):
        """清空场景"""
        self.scene.clear()
        self.frames.clear()
        self.connections.clear()
    
    def add_frame(self, name, x, y):
        """添加坐标系"""
        if name in self.frames:
            return self.frames[name]
        
        frame = TFFrame(name, x, y)
        self.scene.addItem(frame)
        self.frames[name] = frame
        return frame
    
    def add_connection(self, parent_name, child_name):
        """添加连接"""
        if parent_name not in self.frames or child_name not in self.frames:
            return None
        
        parent_frame = self.frames[parent_name]
        child_frame = self.frames[child_name]
        
        connection = TFConnection(parent_frame, child_frame)
        self.scene.addItem(connection)
        self.connections.append(connection)
        
        parent_frame.connections.append(connection)
        child_frame.connections.append(connection)
        
        return connection
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.2
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1.0 / factor, 1.0 / factor)


class TFVisualizerWidget(ROSWidget):
    """TF可视化组件"""
    
    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()
        self._init_ui()
    

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新TF树")
        refresh_btn.clicked.connect(self.refresh_tf_tree)
        toolbar.addWidget(refresh_btn)
        
        expand_btn = QPushButton("展开全部")
        expand_btn.clicked.connect(lambda: self.tf_tree.expandAll())
        toolbar.addWidget(expand_btn)
        
        collapse_btn = QPushButton("折叠全部")
        collapse_btn.clicked.connect(lambda: self.tf_tree.collapseAll())
        toolbar.addWidget(collapse_btn)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # 主要内容区: 标准TF树(左) + 信息面板(右)
        splitter = QSplitter(Qt.Horizontal)
        
        # 标准TF树
        tree_group = QGroupBox("TF坐标系树 (标准树形)")
        tree_layout = QVBoxLayout(tree_group)
        self.tf_tree = QTreeWidget()
        self.tf_tree.setHeaderLabels(["坐标系", "父坐标系", "变换"])
        self.tf_tree.setAlternatingRowColors(True)
        self.tf_tree.itemSelectionChanged.connect(self._on_tree_selected)
        tree_layout.addWidget(self.tf_tree)
        splitter.addWidget(tree_group)
        
        # 信息面板
        info_group = QGroupBox("TF信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        splitter.addWidget(info_group)
        
        splitter.setSizes([600, 300])
        layout.addWidget(splitter)
        
        self._transforms = []  # 保存父子变换(用于信息显示)
        self._frames_map = {}  # frame -> QTreeWidgetItem
    
    def _run_command(self, cmd, timeout=10):
        """运行ROS命令"""
        full_cmd = cmd
        if self.source_cmd:
            full_cmd = f"{self.source_cmd} && {cmd}"
        
        try:
            result = subprocess.run(
                ["bash", "-c", full_cmd],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", 1
        except Exception as e:
            return "", str(e), 1
    
    def refresh_tf_tree(self):
        """刷新TF树(异步,快速获取,不卡界面)"""
        self.tf_tree.clear()
        self.info_text.setPlainText("加载中...")
        
        def worker():
            # 用 rostopic echo 快速获取一帧TF消息(约1秒内返回)
            cmd = "rostopic echo /tf -n 1 2>/dev/null"
            stdout, stderr, code = self._run_command(cmd, timeout=5)
            transforms = []
            if code == 0 and stdout:
                # 解析 /tf 消息中的父子对
                lines = stdout.split("\n")
                cur_parent = None
                for line in lines:
                    line = line.strip()
                    if line.startswith("child_frame_id:"):
                        child = line.split(":", 1)[-1].strip().strip('"')
                        if cur_parent:
                            transforms.append({"parent": cur_parent, "child": child})
                        cur_parent = None
                    elif line.startswith("header:") or "frame_id:" in line and "header" not in line:
                        m = re.search(r'frame_id:\s*"?(\w+)', line)
                        if m and not line.startswith("header"):
                            cur_parent = m.group(1)
            if not transforms:
                # 备用: 尝试 /tf_static
                cmd2 = "rostopic echo /tf_static -n 1 2>/dev/null"
                stdout, _, code2 = self._run_command(cmd2, timeout=4)
                if code2 == 0 and stdout:
                    cur_parent = None
                    for line in stdout.split("\n"):
                        line = line.strip()
                        if line.startswith("child_frame_id:"):
                            child = line.split(":", 1)[-1].strip().strip('"')
                            if cur_parent:
                                transforms.append({"parent": cur_parent, "child": child})
                            cur_parent = None
                        elif line.startswith("frame_id:"):
                            m = re.search(r'frame_id:\s*"?(\w+)', line)
                            if m:
                                cur_parent = m.group(1)
            return transforms

        def on_done(transforms):
            # 防御: 后台异常时收到的是{"error": ...}
            if isinstance(transforms, dict):
                self.info_text.setPlainText(f"获取TF数据出错:\n{transforms.get('error', '未知错误')}")
                return
            self._transforms = transforms
            if not transforms:
                self.info_text.setPlainText(
                    "未获取到TF数据\n\n请确认:\n1. ROS主节点运行中\n2. 有节点在发布/tf话题")
                return
            self._build_tree(transforms)
            self._update_info(transforms)
        
        self._run_bg(worker, on_done)


    def _build_tree(self, transforms):
        """构建标准TF树"""
        self.tf_tree.clear()
        self._frames_map = {}
        
        # 建立父子关系
        children = {}
        parents = {}
        all_frames = set()
        for t in transforms:
            parent = t["parent"]
            child = t["child"]
            all_frames.add(parent)
            all_frames.add(child)
            children.setdefault(parent, []).append(child)
            parents[child] = parent
        
        # 找根节点(无父节点的)
        roots = [f for f in all_frames if f not in parents]
        
        # 递归构建树
        def add_items(parent_item, frame):
            item = QTreeWidgetItem([frame, parents.get(frame, "无")])
            self._frames_map[frame] = item
            if parent_item is None:
                self.tf_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            for child in children.get(frame, []):
                add_items(item, child)
        
        for root in sorted(roots):
            add_items(None, root)
        
        self.tf_tree.expandAll()
        # 选中根节点显示信息
        if self.tf_tree.topLevelItemCount() > 0:
            self.tf_tree.setCurrentItem(self.tf_tree.topLevelItem(0))

    def _on_tree_selected(self):
        """选中树节点显示信息"""
        item = self.tf_tree.currentItem()
        if not item:
            return
        frame = item.text(0)
        # 找出与该frame相关的变换
        lines = []
        for t in self._transforms:
            if t["parent"] == frame:
                lines.append(f"{t['parent']} -> {t['child']}")
            elif t["child"] == frame:
                lines.append(f"{t['parent']} -> {t['child']}")
        self.info_text.setPlainText(f"坐标系: {frame}\n父坐标系: {item.text(1)}\n\n相关变换:\n" + "\n".join(lines))

    def _update_info(self, transforms):
        """更新信息面板"""
        frames = set()
        for t in transforms:
            frames.add(t["parent"])
            frames.add(t["child"])
        info = f"TF坐标系总数: {len(frames)}\n"
        info += f"变换关系数: {len(transforms)}\n\n"
        info += "坐标系列表:\n" + ", ".join(sorted(frames))
        self.info_text.setPlainText(info)

