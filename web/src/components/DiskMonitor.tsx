import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface DiskRow {
  filesystem: string;
  size: string;
  used: string;
  avail: string;
  use: number;
  mounted: string;
}

function parseDf(output: string): DiskRow[] {
  return output
    .split("\n")
    .map((line) => line.trim().split(/\s+/))
    .filter((parts) => parts.length >= 6 && parts[4].endsWith("%"))
    .map((parts) => ({
      filesystem: parts[0],
      size: parts[1],
      used: parts[2],
      avail: parts[3],
      use: parseInt(parts[4].replace("%", ""), 10) || 0,
      mounted: parts.slice(5).join(" "),
    }));
}

function useColor(use: number): string {
  if (use > 90) return "bg-apple-red";
  if (use > 70) return "bg-apple-orange";
  return "bg-apple-green";
}

export default function DiskMonitorPage() {
  const [rows, setRows] = useState<DiskRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    if (loading) return;
    setLoading(true);
    setError("");
    const res = await api.rosExec("df -h 2>/dev/null | head -10", 5).catch(
      () => ({ success: false, output: "", error: "请求失败" })
    );
    setLoading(false);
    if (res.error) {
      setError(`执行出错：${res.error}`);
      setRows([]);
    } else if (!res.output.trim()) {
      setError("未获取到磁盘信息");
      setRows([]);
    } else {
      setRows(parseDf(res.output));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const root = rows.find((r) => r.mounted === "/");

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-5 max-w-3xl"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">磁盘监控</h2>
        <SpringButton
          variant="secondary"
          className="px-5 py-2 font-medium"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? "刷新中…" : "刷新"}
        </SpringButton>
      </div>

      {root && (
        <GlassCard strong className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-[--text-secondary]">根分区 (/)</span>
              <span className="text-2xl font-bold">{root.use}%</span>
            </div>
            <div className="mt-2 h-3 rounded-full bg-black/5 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(root.use, 100)}%` }}
                transition={{ type: "spring", stiffness: 80, damping: 20 }}
                className={`h-full rounded-full ${useColor(root.use)}`}
              />
            </div>
            <div className="mt-1 text-xs text-[--text-tertiary]">
              已用 {root.used} / 共 {root.size}，可用 {root.avail}
            </div>
          </div>
        </GlassCard>
      )}

      {error && (
        <GlassCard className="bg-apple-red/10 text-apple-red text-sm">
          {error}
        </GlassCard>
      )}

      {rows.length > 0 && (
        <GlassCard className="space-y-4 overflow-x-auto">
          <div className="min-w-[560px] space-y-1">
            <div className="grid grid-cols-[1.6fr_0.8fr_0.8fr_0.8fr_1.4fr] gap-3 px-3 py-2 text-xs font-medium text-[--text-tertiary]">
              <span>文件系统</span>
              <span>容量</span>
              <span>已用</span>
              <span>可用</span>
              <span>挂载点</span>
            </div>
            {rows.map((r) => (
              <div
                key={`${r.filesystem}-${r.mounted}`}
                className="grid grid-cols-[1.6fr_0.8fr_0.8fr_0.8fr_1.4fr] items-center gap-3 px-3 py-2.5 rounded-xl bg-white/40"
              >
                <span className="text-sm font-mono truncate" title={r.filesystem}>
                  {r.filesystem}
                </span>
                <span className="text-sm">{r.size}</span>
                <span className="text-sm">{r.used}</span>
                <span className="text-sm">{r.avail}</span>
                <span className="text-sm truncate" title={r.mounted}>
                  {r.mounted}
                </span>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            {rows.map((r) => (
              <div key={`bar-${r.filesystem}-${r.mounted}`} className="space-y-1">
                <div className="flex justify-between text-xs text-[--text-secondary]">
                  <span className="font-mono truncate">{r.mounted || r.filesystem}</span>
                  <span
                    className={
                      r.use > 90
                        ? "text-apple-red font-bold"
                        : r.use > 70
                          ? "text-apple-orange font-bold"
                          : ""
                    }
                  >
                    {r.use}%
                  </span>
                </div>
                <div className="h-2.5 rounded-full bg-black/5 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(r.use, 100)}%` }}
                    transition={{ type: "spring", stiffness: 80, damping: 20 }}
                    className={`h-full rounded-full ${useColor(r.use)}`}
                  />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {!loading && rows.length === 0 && !error && (
        <GlassCard className="text-sm text-[--text-tertiary]">
          暂无磁盘数据，点击“刷新”获取
        </GlassCard>
      )}
    </motion.div>
  );
}
