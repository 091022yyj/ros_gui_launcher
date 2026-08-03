#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微交互动画工具
- 按钮按下透明度反馈(轻量可靠)
- 面板淡入
- 缓动曲线
"""
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect


def add_press_effect(button, pressed_opacity=0.7, duration=100):
    """按钮按下透明度反馈: 按下变暗,松开恢复"""
    try:
        effect = QGraphicsOpacityEffect(button)
        button.setGraphicsEffect(effect)
        button._press_effect = effect

        orig_press = button.mousePressEvent
        orig_release = button.mouseReleaseEvent

        def animate(opacity, dur):
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(dur)
            anim.setStartValue(effect.opacity())
            anim.setEndValue(opacity)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            button._press_anim = anim  # 防GC

        def press_event(event):
            orig_press(event)
            animate(pressed_opacity, duration)

        def release_event(event):
            orig_release(event)
            animate(1.0, duration)

        button.mousePressEvent = press_event
        button.mouseReleaseEvent = release_event
    except Exception:
        pass  # 动画失败不影响功能


def add_fade_in(widget, duration=200):
    """面板淡入效果"""
    try:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        widget._fade_anim = anim  # 防GC
    except Exception:
        pass
