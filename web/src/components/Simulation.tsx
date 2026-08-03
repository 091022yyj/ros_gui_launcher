import { useEffect, useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

/** 仿真控制页 */
export default function SimulationPage() {
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [modelName, setModelName] = useState("");
  const [msg, setMsg] = useState("");

  const refresh = async () => {
    setBusy(true);
    try {
      const res = await api.gazeboStatus();
      setRunning(res.running);
    } catch {
      setRunning(false);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const control = async (action: string, data: Record<string, unknown> = {}) => {
    setBusy(true);
    try {
      const res = await api.gazeboControl(action, data);
      setMsg(res.success ? `操作成功: ${action}` : `操作失败: ${res.error || "未知错误"}`);
      await refresh();
    } catch {
      setMsg("请求失败,请确认后端服务已启动");
    } finally {
      setBusy(false);
    }
  };

  const exec = async (cmd: string, timeout: number, okMsg: string) => {
    setBusy(true);
    try {
      const res = await api.rosExec(cmd, timeout);
      setMsg(res.success ? okMsg : `命令执行失败: ${res.error || "未知错误"}`);
    } catch {
      setMsg("请求失败,请确认后端服务已启动");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">仿真控制</h2>
        <SpringButton variant="secondary" onClick={refresh} disabled={busy}>
          {busy ? "刷新中..." : "🔄 刷新状态"}
        </SpringButton>
      </div>

      <GlassCard className="p-6">
        <div className="flex items-center justify-between">
          <span className="text-sm text-[--text-secondary]">Gazebo 状态</span>
          <span className="flex items-center gap-2 text-sm font-semibold">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: running ? "#34c759" : "#ff3b30" }}
            />
            Gazebo: {running ? "运行中" : "未运行"}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3">
          <SpringButton variant="secondary" onClick={() => control("pause")} disabled={busy || !running}>
            ⏸ 暂停
          </SpringButton>
          <SpringButton variant="secondary" onClick={() => control("unpause")} disabled={busy || !running}>
            ▶ 继续
          </SpringButton>
          <SpringButton variant="secondary" onClick={() => control("reset")} disabled={busy || !running}>
            🔄 重置
          </SpringButton>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <SpringButton
            variant="primary"
            disabled={busy}
            onClick={() =>
              exec("roslaunch gazebo_ros empty_world.launch &", 3, "Gazebo 启动命令已发送")
            }
          >
            🚀 启动Gazebo
          </SpringButton>
          <SpringButton
            variant="danger"
            disabled={busy}
            onClick={() => exec("pkill -f gzserver; pkill -f gazebo", 3, "Gazebo 停止命令已发送")}
          >
            ⏹ 停止Gazebo
          </SpringButton>
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <h3 className="font-semibold mb-3">模型管理</h3>
        <div className="flex gap-3">
          <input
            className="flex-1 bg-white/70 border border-black/10 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-apple-blue"
            placeholder="输入模型名称"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
          />
          <SpringButton
            variant="danger"
            disabled={busy || !modelName.trim()}
            onClick={() => {
              control("delete", { name: modelName.trim() }).then(() => setModelName(""));
            }}
          >
            删除模型
          </SpringButton>
        </div>
      </GlassCard>

      {msg && <div className="text-sm text-[--text-secondary] px-1">{msg}</div>}
    </div>
  );
}
