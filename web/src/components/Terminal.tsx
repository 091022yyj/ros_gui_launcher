import { useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";

/** 终端页(前端模拟终端) */
export function Terminal() {
  const [input, setInput] = useState("");
  const [lines, setLines] = useState<string[]>([
    "ROS GUI 启动器 终端",
    "输入命令执行 (如: rostopic list)",
    "---",
  ]);

  const run = () => {
    if (!input.trim()) return;
    setLines((ls) => [...ls, `$ ${input}`]);
    // 通过后端执行(预留)
    setLines((ls) => [...ls, "→ 命令已发送(后端执行中...)"]);
    setInput("");
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">终端</h2>
      <GlassCard className="p-4 !bg-black/80">
        <div className="h-96 overflow-y-auto font-mono text-sm text-green-400 space-y-1">
          {lines.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
        <div className="flex gap-2 mt-3">
          <input
            className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-white outline-none focus:border-apple-blue"
            placeholder="输入ROS命令..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
          />
          <SpringButton variant="primary" onClick={run}>
            执行
          </SpringButton>
        </div>
      </GlassCard>
    </div>
  );
}
