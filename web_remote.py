#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web远程访问模块
- 启动 rosbridge_server,让手机/浏览器远程访问
- 在 web 目录生成基于 roslibjs 的遥控页面(index.html)
- 键盘方向键控制小车 cmd_vel,摄像头画面 iframe 占位
- 通过 python3 -m http.server 提供 8888 端口静态页面服务
"""
import os
import signal
import subprocess
import webbrowser
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QMessageBox)

# index.html 模板,__ROSBRIDGE_IP__ 启动前替换为本机IP
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ROS小车远程控制</title>
<script src="https://static.ros.org/js/roslib.js"></script>
<style>
    body { background: #1e1f29; color: #f8f8f2; font-family: sans-serif;
           text-align: center; margin: 0; padding: 16px; }
    h1 { color: #50fa7b; font-size: 22px; }
    .tip { color: #6272a4; font-size: 13px; margin: 8px 0 16px 0; }
    #status { color: #6272a4; font-size: 14px; margin-bottom: 16px; }
    #camera { width: 100%; max-width: 640px; height: 360px;
              background: #282a36; border: 2px dashed #44475a;
              border-radius: 8px; margin: 0 auto 16px auto; display: block; }
    .keys { font-size: 15px; color: #f8f8f2; background: #282a36;
            border: 1px solid #44475a; border-radius: 10px; padding: 16px;
            max-width: 420px; margin: 0 auto; line-height: 2; }
    kbd { background: #44475a; color: #50fa7b; border-radius: 4px;
          padding: 2px 8px; font-weight: bold; }
</style>
</head>
<body>
<h1>🚗 ROS小车远程控制</h1>
<p class="tip">本页面已连接 rosbridge,使用键盘方向键控制小车</p>
<p id="status">正在连接 ws://__ROSBRIDGE_IP__:9090 ...</p>
<iframe id="camera" src="about:blank" frameborder="0"
        title="摄像头画面占位(待接入)"></iframe>
<div class="keys">
    方向键 <kbd>↑</kbd><kbd>↓</kbd> 前进/后退 &nbsp;|&nbsp;
    <kbd>←</kbd><kbd>→</kbd> 转向<br>
    松开按键即停止,<kbd>空格</kbd> 紧急停止
</div>
<script>
    var ip = "__ROSBRIDGE_IP__";
    var ros = new ROSLIB.Ros({ url: "ws://" + ip + ":9090" });
    var statusEl = document.getElementById("status");
    ros.on("connection", function() {
        statusEl.innerHTML = "✅ 已连接 rosbridge: ws://" + ip + ":9090";
        statusEl.style.color = "#50fa7b";
    });
    ros.on("error", function() {
        statusEl.innerHTML = "❌ 连接失败,请确认 rosbridge_server 已启动";
        statusEl.style.color = "#ff5555";
    });
    ros.on("close", function() {
        statusEl.innerHTML = "⚠️ 连接已断开,正在重连...";
        statusEl.style.color = "#f1fa8c";
        setTimeout(function() { ros.connect("ws://" + ip + ":9090"); }, 2000);
    });

    var cmdVel = new ROSLIB.Topic({
        ros: ros, name: "/cmd_vel", messageType: "geometry_msgs/Twist"
    });
    var keys = { up: false, down: false, left: false, right: false };

    function publish() {
        var linear = 0, angular = 0;
        if (keys.up) linear = 0.3;
        if (keys.down) linear = -0.3;
        if (keys.left) angular = 0.5;
        if (keys.right) angular = -0.5;
        var twist = new ROSLIB.Message({
            linear: { x: linear, y: 0, z: 0 },
            angular: { x: 0, y: 0, z: angular }
        });
        cmdVel.publish(twist);
    }

    document.addEventListener("keydown", function(e) {
        if (e.key === "ArrowUp") { keys.up = true; e.preventDefault(); }
        if (e.key === "ArrowDown") { keys.down = true; e.preventDefault(); }
        if (e.key === "ArrowLeft") { keys.left = true; e.preventDefault(); }
        if (e.key === "ArrowRight") { keys.right = true; e.preventDefault(); }
        if (e.key === " ") { keys.up = keys.down = keys.left = keys.right = false; e.preventDefault(); }
        publish();
    });
    document.addEventListener("keyup", function(e) {
        if (e.key === "ArrowUp") keys.up = false;
        if (e.key === "ArrowDown") keys.down = false;
        if (e.key === "ArrowLeft") keys.left = false;
        if (e.key === "ArrowRight") keys.right = false;
        publish();
    });
    window.setInterval(publish, 100);  // 10Hz 持续发送,防止按键丢失
</script>
</body>
</html>
"""


class WebRemoteWidget(QWidget):
    """Web远程访问面板"""

    def __init__(self, ros_setup="", ws_setup="", parent=None):
        super().__init__(parent)
        self.ros_setup = ros_setup
        self.ws_setup = ws_setup
        self.process = None
        self.web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        self.local_ip = "localhost"
        self._build_source_cmd()
        self._init_ui()
        self._refresh_ip()

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

    def _get_local_ip(self):
        try:
            out = subprocess.run(["hostname", "-I"], capture_output=True,
                                 text=True, timeout=3).stdout.strip()
            if out:
                return out.split()[0]
        except Exception:
            pass
        return "localhost"

    def _refresh_ip(self):
        self.local_ip = self._get_local_ip()
        self.info_label.setText(
            f"手机连接同一WiFi后访问 http://{self.local_ip}:8888/index.html")

    def _generate_index_html(self):
        ip = self.local_ip if self.local_ip != "localhost" else "127.0.0.1"
        os.makedirs(self.web_dir, exist_ok=True)
        index_path = os.path.join(self.web_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(INDEX_TEMPLATE.replace("__ROSBRIDGE_IP__", ip))
        return index_path

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 状态显示
        status_group = QGroupBox("服务状态")
        status_layout = QHBoxLayout(status_group)
        status_layout.addWidget(QLabel("状态:"))
        self.status_label = QLabel("未启动")
        self.status_label.setStyleSheet("color: #6272a4; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addWidget(status_group)

        # 控制按钮
        btn_group = QGroupBox("Web服务控制")
        btn_layout = QVBoxLayout(btn_group)
        self.start_btn = QPushButton("启动Web服务")
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #50fa7b; color: #1e1f29;
                font-size: 15px; font-weight: bold; padding: 10px;
                border-radius: 8px; }
            QPushButton:hover { background-color: #69ff94; }
            QPushButton:disabled { background-color: #44475a; color: #6272a4; }
        """)
        self.start_btn.clicked.connect(self.start_web)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止Web服务")
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #44475a; color: #ff5555;
                font-size: 15px; font-weight: bold; padding: 10px;
                border-radius: 8px; }
            QPushButton:hover { background-color: #ff5555; color: white; }
            QPushButton:disabled { background-color: #282a36; color: #6272a4; }
        """)
        self.stop_btn.clicked.connect(self.stop_web)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        self.open_btn = QPushButton("打开控制页面")
        self.open_btn.setStyleSheet("""
            QPushButton { background-color: #6272a4; color: white;
                font-size: 14px; padding: 8px; border-radius: 8px; }
            QPushButton:hover { background-color: #7a8bd1; }
        """)
        self.open_btn.clicked.connect(self.open_page)
        btn_layout.addWidget(self.open_btn)
        layout.addWidget(btn_group)

        # 访问说明
        info_group = QGroupBox("使用说明")
        info_layout = QVBoxLayout(info_group)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #f1fa8c;")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        note = QLabel("请先确保小车底盘与 rosbridge_server 在同一网络中,\n"
                      "手机浏览器打开上方地址即可用方向键远程控制小车。")
        note.setStyleSheet("color: #6272a4;")
        note.setWordWrap(True)
        info_layout.addWidget(note)
        layout.addWidget(info_group)

        layout.addStretch()

    def start_web(self):
        if self.process is not None:
            return
        self._generate_index_html()
        cmd = (f"{self.source_cmd} && "
               f"roslaunch rosbridge_server rosbridge_websocket.launch & "
               f"python3 -m http.server 8888 --bind 0.0.0.0 "
               f"--directory '{self.web_dir}'")
        try:
            self.process = subprocess.Popen(
                ["bash", "-c", cmd], preexec_fn=os.setsid)
        except Exception as e:
            QMessageBox.critical(self, "启动失败", f"启动Web服务失败:\n{e}")
            self.process = None
            return
        self.status_label.setText("运行中")
        self.status_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_web(self):
        if self.process is None:
            return
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        except Exception:
            pass
        try:
            self.process.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except Exception:
                pass
        self.process = None
        self.status_label.setText("未启动")
        self.status_label.setStyleSheet("color: #6272a4; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def open_page(self):
        webbrowser.open("http://localhost:8888/index.html")
