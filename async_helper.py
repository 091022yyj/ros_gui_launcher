#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨线程回调安全中转
- QTimer.singleShot 从后台线程调用时回调不会执行(进入不存在的线程事件循环)
- 用 pyqtSignal 队列连接实现线程安全回调
- 每次调用使用独立信号对象,避免多个异步操作信号串扰
"""
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class _SignalBridge(QObject):
    """独立信号中转(在主线程创建,emit跨线程安全)"""
    result = pyqtSignal(object)


def run_async(fn, on_done=None):
    """后台线程执行fn,完成后在主线程调用on_done(result)
    线程安全,不阻塞主线程UI
    """
    if on_done is None:
        def worker_no_cb():
            try:
                fn()
            except Exception:
                pass
        threading.Thread(target=worker_no_cb, daemon=True).start()
        return

    # 每次调用独立信号对象,避免并发异步操作互相串扰
    bridge = _SignalBridge()

    def handler(result):
        try:
            on_done(result)
        finally:
            bridge.result.disconnect(handler)

    bridge.result.connect(handler)

    def worker():
        try:
            result = fn()
        except Exception as e:
            import traceback
            result = {"error": "%s: %s" % (type(e).__name__, str(e)),
                      "traceback": traceback.format_exc()}
        bridge.result.emit(result)

    threading.Thread(target=worker, daemon=True).start()
