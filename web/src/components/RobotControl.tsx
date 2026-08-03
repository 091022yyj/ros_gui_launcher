import { useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

function buildCmd(linear: number, angular: number): string {
  const l = linear.toFixed(1);
  const a = angular.toFixed(1);
  return `rostopic pub -1 /cmd_vel geometry_msgs/Twist '{linear: {x: ${l}, y: 0, z: 0}, angular: {x: 0, y: 0, z: ${a}}}'`;
}

export default function RobotControlPage() {
  const [linearSpeed, setLinearSpeed] = useState(0.3);
  const [angularSpeed, setAngularSpeed] = useState(0.5);
  const [status, setStatus] = useState("就绪");
  const [busy, setBusy] = useState(false);

  async function sendMove(linear: number, angular: number, label: string) {
    if (busy) return;
    setBusy(true);
    setStatus(`${label}中…`);
    const res = await api.rosExec(buildCmd(linear, angular), 3).catch(() => ({
      success: false,
      output: "",
      error: "请求失败",
    }));
    setBusy(false);
    setStatus(
      res.success ? `${label}完成` : `${label}失败：${res.error || "未知错误"}`
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-5 max-w-2xl"
    >
      <h2 className="text-xl font-bold">遥控面板</h2>

      <GlassCard className="space-y-6">
        <div className="grid grid-cols-3 gap-2 w-56 mx-auto">
          <div />
          <SpringButton
            className="text-2xl h-14"
            onClick={() => sendMove(linearSpeed, 0, "前进")}
            disabled={busy}
          >
            ↑
          </SpringButton>
          <div />
          <SpringButton
            className="text-2xl h-14"
            onClick={() => sendMove(0, -angularSpeed, "左转")}
            disabled={busy}
          >
            ←
          </SpringButton>
          <div className="flex items-center justify-center">
            <div className="w-8 h-8 rounded-full bg-black/10 text-[--text-tertiary] flex items-center justify-center text-xs">
              停
            </div>
          </div>
          <SpringButton
            className="text-2xl h-14"
            onClick={() => sendMove(0, angularSpeed, "右转")}
            disabled={busy}
          >
            →
          </SpringButton>
          <div />
          <SpringButton
            className="text-2xl h-14"
            onClick={() => sendMove(-linearSpeed, 0, "后退")}
            disabled={busy}
          >
            ↓
          </SpringButton>
          <div />
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-[--text-secondary]">线速度</span>
              <span className="font-mono text-apple-blue">
                {linearSpeed.toFixed(1)} m/s
              </span>
            </div>
            <input
              type="range"
              min={0.1}
              max={1.0}
              step={0.1}
              value={linearSpeed}
              onChange={(e) => setLinearSpeed(Number(e.target.value))}
              className="w-full accent-apple-blue"
            />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-[--text-secondary]">角速度</span>
              <span className="font-mono text-apple-blue">
                {angularSpeed.toFixed(1)} rad/s
              </span>
            </div>
            <input
              type="range"
              min={0.1}
              max={1.0}
              step={0.1}
              value={angularSpeed}
              onChange={(e) => setAngularSpeed(Number(e.target.value))}
              className="w-full accent-apple-orange"
            />
          </div>
        </div>

        <div className="flex items-center justify-center gap-4">
          <SpringButton
            variant="danger"
            className="px-10 py-4 text-lg font-bold"
            onClick={() => sendMove(0, 0, "紧急停止")}
            disabled={busy}
          >
            紧急停止
          </SpringButton>
        </div>

        <motion.div
          className={`text-center text-sm rounded-xl py-2 px-4 ${
            status.includes("失败")
              ? "bg-apple-red/10 text-apple-red"
              : status.includes("中")
                ? "bg-apple-orange/10 text-apple-orange"
                : "bg-apple-green/10 text-apple-green"
          }`}
          animate={{ opacity: busy ? 0.7 : 1 }}
        >
          {status}
        </motion.div>
      </GlassCard>
    </motion.div>
  );
}
