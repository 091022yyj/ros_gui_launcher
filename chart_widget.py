#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时趋势图表组件
- QPainter自绘折线图,无需额外依赖
- 支持多序列数据(CPU/内存等)
- 渐变填充 + 网格线 + 当前值显示
"""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPen, QPainter, QPainterPath, QFont, QLinearGradient
from PyQt6.QtWidgets import QWidget
from collections import deque


class TrendChartWidget(QWidget):
    """实时趋势图"""

    def __init__(self, parent=None, max_points=80):
        super().__init__(parent)
        self.max_points = max_points
        self.series = {}
        self.series_colors = {}
        self.series_labels = {}
        self.setMinimumHeight(160)
        self.setMinimumWidth(320)

    def add_series(self, name, color="#8be9fd", label=None):
        """添加数据序列"""
        self.series[name] = deque(maxlen=self.max_points)
        self.series_colors[name] = QColor(color)
        self.series_labels[name] = label or name

    def add_data_point(self, name, value):
        """添加数据点"""
        if name in self.series:
            self.series[name].append(float(value))
            self.update()

    def clear(self):
        """清空数据"""
        for name in self.series:
            self.series[name].clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 8

        # 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1e1f29"))
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        # 边框
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#44475a"), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        # 绘图区域
        plot_rect = QRectF(margin + 30, margin + 5, w - 2 * margin - 30, h - 2 * margin - 28)

        # 网格线(水平虚线) + Y轴刻度
        grid_color = QColor("#33363f")
        grid_pen = QPen(grid_color, 1)
        grid_pen.setStyle(Qt.PenStyle.DashLine)

        y_label_font = QFont()
        y_label_font.setPointSize(8)
        painter.setFont(y_label_font)

        for i in range(5):
            y = plot_rect.top() + plot_rect.height() * i / 4
            painter.setPen(grid_pen)
            painter.drawLine(plot_rect.left(), y, plot_rect.right(), y)

            # Y轴刻度文字
            value = 100 - (100 * i / 4)
            painter.setPen(QColor("#6272a4"))
            painter.drawText(
                QRectF(margin, y - 8, 28, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.0f}%"
            )

        # 垂直线(3条)
        for i in range(1, 4):
            x = plot_rect.left() + plot_rect.width() * i / 4
            painter.setPen(grid_pen)
            painter.drawLine(x, plot_rect.top(), x, plot_rect.bottom())

        # 绘制各序列
        for name, data in self.series.items():
            if len(data) < 2:
                continue

            color = self.series_colors.get(name, QColor("#8be9fd"))
            color_alpha = QColor(color)

            # 计算点坐标
            max_len = self.max_points
            n = len(data)
            start_idx = max(0, n - max_len)
            points = []

            for i, val in enumerate(list(data)[start_idx:]):
                x = plot_rect.left() + plot_rect.width() * i / (max_len - 1) if max_len > 1 else plot_rect.left()
                v = max(0, min(100, val))
                y = plot_rect.bottom() - plot_rect.height() * v / 100
                points.append((x, y))

            if len(points) < 2:
                continue

            # 渐变填充
            fill_path = QPainterPath()
            fill_path.moveTo(points[0][0], plot_rect.bottom())
            for x, y in points:
                fill_path.lineTo(x, y)
            fill_path.lineTo(points[-1][0], plot_rect.bottom())
            fill_path.closeSubpath()

            gradient = QLinearGradient(0, plot_rect.top(), 0, plot_rect.bottom())
            gradient.setColorAt(0, QColor(color_alpha.red(), color_alpha.green(), color_alpha.blue(), 70))
            gradient.setColorAt(1, QColor(color_alpha.red(), color_alpha.green(), color_alpha.blue(), 10))
            painter.fillPath(fill_path, gradient)

            # 折线
            line_path = QPainterPath()
            line_path.moveTo(points[0][0], points[0][1])
            for x, y in points[1:]:
                line_path.lineTo(x, y)

            painter.setBrush(Qt.NoBrush)
            pen = QPen(color, 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(line_path)

            # 最后一个点画圆
            last_x, last_y = points[-1]
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(last_x - 3.5, last_y - 3.5, 7, 7))

            # 当前值标签
            painter.setFont(y_label_font)
            painter.setPen(color)
            painter.drawText(
                QRectF(last_x + 5, last_y - 12, 60, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{data[-1]:.1f}%"
            )

        # 图例
        legend_y = h - 15
        legend_x = margin + 30
        painter.setFont(y_label_font)
        for name, data in self.series.items():
            color = self.series_colors.get(name, QColor("#8be9fd"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(legend_x, legend_y, 10, 10), 2, 2)
            painter.setPen(QColor("#f8f8f2"))
            label = self.series_labels.get(name, name)
            painter.drawText(QRectF(legend_x + 14, legend_y - 3, 80, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            legend_x += 14 + painter.fontMetrics().width(label) + 20

        painter.end()
