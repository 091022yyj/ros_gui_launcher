#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS GUI Launcher - Python后端API服务
- FastAPI提供REST API + WebSocket
- 复用现有业务模块(process/config/log/scene)
- 前端(Tauri+React)通过HTTP/WS通信
启动: uvicorn main:app --host 0.0.0.0 --port 8000
"""
import os
import sys
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ROS GUI Launcher API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:3000", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from constants import BASE_DIR, CONFIG_FILE, DEFAULT_CONFIG, VERSION


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": VERSION}


@app.get("/api/system/info")
def system_info():
    info = {"version": VERSION, "base_dir": str(BASE_DIR)}
    try:
        import psutil
        info["cpu"] = psutil.cpu_percent(interval=0.1)
        info["memory"] = psutil.virtual_memory().percent
        info["disk"] = psutil.disk_usage("/").percent
        info["hostname"] = os.uname().nodename
    except Exception:
        pass
    return info


@app.get("/api/config")
def get_config():
    return {"config": _load_config()}


@app.post("/api/config")
async def save_config(config: dict):
    try:
        merged = dict(DEFAULT_CONFIG)
        merged.update(config)
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_FILE)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/tasks")
def get_tasks():
    cfg = _load_config()
    return {"tasks": {"launch": cfg.get("launch_files", []),
                      "py": cfg.get("py_files", [])}}


@app.post("/api/tasks/{kind}/start")
async def start_task(kind: str, task: dict):
    try:
        cfg = _load_config()
        path = task.get("path", "")
        args = task.get("args", "")
        if not path or not os.path.exists(path):
            return {"success": False, "error": "文件不存在: %s" % path}

        parts = []
        ros_setup = cfg.get("ros_setup", "")
        if ros_setup and os.path.exists(ros_setup):
            parts.append("source '%s'" % ros_setup)
        ws = cfg.get("ws_setup", "") or os.path.expanduser("~/catkin_ws/devel/setup.bash")
        if os.path.exists(ws):
            parts.append("source '%s'" % ws)
        if kind == "launch":
            parts.append("roslaunch '%s'" % path)
        else:
            parts.append("python3 '%s'" % path)
        if args:
            parts[-1] += " " + args
        cmd = " && ".join(parts) + " &"

        import subprocess
        subprocess.Popen(["bash", "-c", cmd], preexec_fn=os.setsid)
        return {"success": True, "command": cmd}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/tasks/stop")
async def stop_task(task: dict):
    try:
        path = task.get("path", "")
        if not path:
            return {"success": False, "error": "缺少path"}
        name = os.path.basename(path)
        import subprocess
        subprocess.Popen(["bash", "-c",
                          "pkill -f '%s' 2>/dev/null; pkill -f 'roslaunch.*%s' 2>/dev/null" % (name, name)],
                         preexec_fn=os.setsid)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/ros/nodes")
def ros_nodes():
    try:
        import subprocess
        r = subprocess.run(["bash", "-c", "source /opt/ros/noetic/setup.bash && rosnode list 2>/dev/null"],
                           capture_output=True, text=True, timeout=8)
        nodes = [n for n in r.stdout.split("\n") if n.strip()]
        return {"nodes": nodes}
    except Exception as e:
        return {"nodes": [], "error": str(e)}


@app.get("/api/ros/topics")
def ros_topics():
    try:
        import subprocess
        r = subprocess.run(["bash", "-c", "source /opt/ros/noetic/setup.bash && rostopic list 2>/dev/null"],
                           capture_output=True, text=True, timeout=8)
        topics = [t for t in r.stdout.split("\n") if t.strip()]
        return {"topics": topics}
    except Exception as e:
        return {"topics": [], "error": str(e)}


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    """日志实时推送"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"echo": data}))
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
