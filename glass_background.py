#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
液态玻璃背景组件
- 渐变底色 + 彩色模糊圆斑(blob)动态漂浮
- 借鉴Tauri版UI设计的玻璃质感
"""
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QRadialGradient, QBrush
from PyQt6.QtWidgets import QWidget


class GlassBackground(QWidget):
    """液态玻璃背景(放在所有内容下方)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blobs = [
            {"pos": QPointF(0.1, 0.1), "size": 300, "color": QColor(0, 113, 227, 90),
             "vel": QPointF(0.15, 0.12)},
            {"pos": QPointF(0.7, 0.2), "size": 240, "color": QColor(175, 82, 222, 80),
             "vel": QPointF(-0.1, 0.18)},
            {"pos": QPointF(0.5, 0.75), "size": 260, "color": QColor(52, 199, 89, 75),
             "vel": QPointF(0.12, -0.13)},
        ]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)  # ~30fps漂浮动画

    def pause_timers(self):
        self.timer.stop()

    def resume_timers(self):
        self.timer.start(33)

    def _tick(self):
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        for b in self.blobs:
            b["pos"] += b["vel"]
            # 边界反弹
            if b["pos"].x() < 0 or b["pos"].x() > 1:
                b["vel"].setX(-b["vel"].x())
            if b["pos"].y() < 0 or b["pos"].y() > 1:
                b["vel"].setY(-b["vel"].y())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # 渐变底色(浅色液态玻璃风格)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(245, 245, 247))
        grad.setColorAt(1, QColor(235, 238, 245))
        painter.fillRect(0, 0, w, h, grad)

        # 绘制模糊blob(用径向渐变模拟模糊)
        for b in self.blobs:
            cx = b["pos"].x() * w
            cy = b["pos"].y() * h
            r = b["size"]
            radial = QRadialGradient(cx, cy, r)
            color = b["color"]
            radial.setColorAt(0, color)
            color_center = QColor(color)
            color_center.setAlpha(color.alpha() // 3)
            radial.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(QBrush(radial))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        painter.end()
