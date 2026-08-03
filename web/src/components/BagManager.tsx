import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface BagFile {
  name: string;
  size: string;
}

/** rosbag 管理页 */
export default function BagManagerPage() {
  const [recording, setRecording] = useState(false);
  const [bags, setBags] = useState<BagFile[]>([]);
  const [playName, setPlayName] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const listBags = async () => {
    const res = await api.rosExec('ls -lh ~/bags/*.bag 2>/dev/null | awk \'{print $NF, $5}\'', 4);
    if (!res.success) {
      setMessage({ ok: false, text: res.error ?? "获取失败" });
      return;
    }
    const lines = res.output.trim().split("\n").filter(Boolean);
    setBags(lines.map((line) => {
      const idx = line.lastIndexOf(" ");
      return {
        name: idx >= 0 ? line.slice(0, idx).split("/").pop() ?? line : line,
        size: idx >= 0 ? line.slice(idx + 1) : "",
      };
    }));
  };

  useEffect(() => {
    listBags();
  }, []);

  const startRecord = async () => {
    setRecording(true);
    setMessage(null);
    const res = await api.rosExec("rosbag record -O ~/bags/record_$(date +%H%M%S).bag -a", 3);
    if (!res.success) {
      setMessage({ ok: false, text: res.error ?? "启动失败" });
      setRecording(false);
    }
  };

  const stopRecord = async () => {
    setRecording(false);
    const res = await api.rosExec("pkill -f rosbag record");
    setMessage(res.success
      ? { ok: true, text: "已停止录制" }
      : { ok: false, text: res.error ?? "停止失败" });
    setTimeout(listBags, 500);
  };

  const play = async () => {
    const name = playName.trim();
    if (!name) return;
    setMessage(null);
    const res = await api.rosExec(`rosbag play ~/bags/${name}`, 3);
    setMessage(res.success
      ? { ok: true, text: `开始播放 ${name}` }
      : { ok: false, text: res.error ?? "播放失败" });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">rosbag管理</h2>
        <SpringButton variant="secondary" onClick={listBags}>
          🔄 刷新列表
        </SpringButton>
      </div>

      {message && (
        <GlassCard className={`p-3 text-sm ${message.ok ? "" : "text-[--text-danger]"}`}>
          {message.text}
        </GlassCard>
      )}

      <div className="grid grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <h3 className="font-semibold text-[15px] mb-3">录制控制</h3>
          <p className="text-xs text-[--text-tertiary] mb-4">
            录制所有话题,文件保存至 ~/bags/
          </p>
          {recording ? (
            <SpringButton variant="danger" className="w-full" onClick={stopRecord}>
              ⏹ 停止录制
            </SpringButton>
          ) : (
            <SpringButton variant="primary" className="w-full" onClick={startRecord}>
              ⏺ 开始录制
            </SpringButton>
          )}
          <div className={`mt-3 text-xs ${recording ? "text-apple-red" : "text-[--text-tertiary]"}`}>
            ● 状态: {recording ? "录制中" : "空闲"}
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <h3 className="font-semibold text-[15px] mb-3">播放</h3>
          <div className="flex gap-2">
            <input
              className="flex-1 px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
              placeholder="输入 bag 文件名"
              value={playName}
              onChange={(e) => setPlayName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && play()}
            />
            <SpringButton onClick={play} disabled={!playName.trim()}>
              ▶ 播放
            </SpringButton>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-[15px]">已有 bag 文件</h3>
          <span className="text-xs text-[--text-tertiary]">共 {bags.length} 个</span>
        </div>
        {bags.length === 0 ? (
          <div className="text-sm text-[--text-tertiary] py-8 text-center">
            ~/bags/ 下暂无 bag 文件
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {bags.map((bag) => (
                <motion.div
                  key={bag.name}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  className="flex items-center gap-3 p-3 rounded-xl bg-white/50 hover:bg-white/80 transition-colors"
                >
                  <span className="w-2 h-2 rounded-full bg-apple-purple" />
                  <span className="flex-1 text-sm truncate">{bag.name}</span>
                  <span className="text-xs text-[--text-tertiary]">{bag.size}</span>
                  <SpringButton variant="secondary" onClick={() => setPlayName(bag.name)}>
                    选中
                  </SpringButton>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
