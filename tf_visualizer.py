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
    QGroupBox, QSplitter, QTextEdit
)


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


class TFVisualizerWidget(QWidget):
    """TF可视化组件"""
    
    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()
        self._init_ui()
    
    def _build_source_cmd(self):
        """构建source命令"""
        parts = []
        if self.ros_setup and os.path.exists(self.ros_setup):
            parts.append(f"source '{self.ros_setup}'")
        if self.ws_setup and os.path.exists(os.path.expanduser(self.ws_setup)):
            parts.append(f"source '{os.path.expanduser(self.ws_setup)}'")
        self.source_cmd = " && ".join(parts) if parts else ""
    
    def set_ros_env(self, ros_setup, ws_setup):
        """设置ROS环境"""
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self._build_source_cmd()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新TF树")
        refresh_btn.clicked.connect(self.refresh_tf_tree)
        toolbar.addWidget(refresh_btn)
        
        auto_layout_btn = QPushButton("自动布局")
        auto_layout_btn.clicked.connect(self.auto_layout)
        toolbar.addWidget(auto_layout_btn)
        
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # 主要内容区
        splitter = QSplitter(Qt.Horizontal)
        
        # 图形视图
        self.graphics_view = TFGraphicsView()
        splitter.addWidget(self.graphics_view)
        
        # 信息面板
        info_group = QGroupBox("TF信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        splitter.addWidget(info_group)
        
        splitter.setSizes([600, 300])
        layout.addWidget(splitter)
    
    def _run_command(self, cmd):
        """运行ROS命令"""
        full_cmd = cmd
        if self.source_cmd:
            full_cmd = f"{self.source_cmd} && {cmd}"
        
        try:
            result = subprocess.run(
                ["bash", "-c", full_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", 1
        except Exception as e:
            return "", str(e), 1
    
    def refresh_tf_tree(self):
        """刷新TF树"""
        self.graphics_view.clear_scene()
        
        # 获取TF帧
        frames_result = self._get_tf_frames()
        if frames_result.get("error"):
            QMessageBox.warning(self, "错误", f"获取TF帧失败:\n{frames_result['error']}")
            return
        
        frames = frames_result.get("frames", [])
        if not frames:
            self.info_text.setPlainText("未发现TF坐标系")
            return
        
        # 获取TF关系
        transforms = self._get_tf_transforms()
        
        # 布局坐标系
        self._layout_frames(frames, transforms)
        
        # 更新信息
        self._update_info(frames, transforms)
    
    def _get_tf_frames(self):
        """获取TF帧"""
        cmd = "rosrun tf tf_monitor"
        stdout, stderr, code = self._run_command(cmd)
        
        if code != 0:
            # 尝试备用命令
            cmd = "rostopic echo /tf -n 1"
            stdout, stderr, code = self._run_command(cmd)
            
            if code != 0:
                return {"frames": [], "error": stderr}
        
        # 解析坐标系
        frames = set()
        for line in stdout.split("\n"):
            match = re.search(r'frame_id:\s*["\']?(\w+)["\']?', line)
            if match:
                frames.add(match.group(1))
            match = re.search(r'child_frame_id:\s*["\']?(\w+)["\']?', line)
            if match:
                frames.add(match.group(1))
        
        return {"frames": sorted(list(frames)), "error": None}
    
    def _get_tf_transforms(self):
        """获取TF变换关系"""
        cmd = "rosrun tf tf_monitor -v"
        stdout, stderr, code = self._run_command(cmd)
        
        transforms = []
        
        for line in stdout.split("\n"):
            # 查找变换关系
            match = re.search(r'(\w+)\s*->\s*(\w+)', line)
            if match:
                parent = match.group(1)
                child = match.group(2)
                transforms.append({"parent": parent, "child": child})
        
        return transforms
    
    def _layout_frames(self, frames, transforms):
        """布局坐标系"""
        # 构建父子关系
        children = {}
        parents = {}
        
        for t in transforms:
            parent = t["parent"]
            child = t["child"]
            
            if parent not in children:
                children[parent] = []
            children[parent].append(child)
            
            parents[child] = parent
        
        # 找到根节点（没有父节点的）
        roots = [f for f in frames if f not in parents]
        
        # 如果没有找到根节点，使用第一个帧
        if not roots and frames:
            roots = [frames[0]]
        
        # 布局
        x_offset = 100
        y_offset = 100
        
        def layout_subtree(frame_name, x, y, level=0):
            """递归布局子树"""
            frame = self.graphics_view.add_frame(frame_name, x, y)
            
            if frame_name in children:
                child_y_offset = 150
                for i, child in enumerate(children[frame_name]):
                    child_x = x + (i - len(children[frame_name]) / 2) * 150
                    child_y = y + child_y_offset
                    
                    self.graphics_view.add_connection(frame_name, child)
                    layout_subtree(child, child_x, child_y, level + 1)
        
        # 布局每个根节点
        for i, root in enumerate(roots):
            layout_subtree(root, x_offset + i * 200, y_offset)
    
    def auto_layout(self):
        """自动重新布局"""
        self.refresh_tf_tree()
    
    def zoom_in(self):
        """放大"""
        self.graphics_view.scale(1.2, 1.2)
    
    def zoom_out(self):
        """缩小"""
        self.graphics_view.scale(1.0 / 1.2, 1.0 / 1.2)
    
    def _update_info(self, frames, transforms):
        """更新信息面板"""
        info = []
        info.append(f"TF坐标系数量: {len(frames)}")
        info.append(f"TF变换数量: {len(transforms)}")
        info.append("")
        info.append("坐标系列表:")
        for frame in frames:
            info.append(f"  - {frame}")
        
        if transforms:
            info.append("")
            info.append("变换关系:")
            for t in transforms:
                info.append(f"  {t['parent']} -> {t['child']}")
        
        self.info_text.setPlainText("\n".join(info))
