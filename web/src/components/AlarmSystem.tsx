import { useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface AlarmRecord {
  time: string;
  item: string;
  status: string;
  ok: boolean;
}

const GREEN = "#34c759";
const RED = "#ff3b30";

/** 报警系统页 */
export default function AlarmSystemPage() {
  const [records, setRecords] = useState<AlarmRecord[]>([]);
  const [busy, setBusy] = useState(false);

  const addRecord = (item: string, status: string, ok: boolean) => {
    const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    setRecords((prev) => [{ time, item, status, ok }, ...prev].slice(0, 50));
  };

  const check = async () => {
    setBusy(true);
    try {
      const master = await api.rosExec("rostopic list 2>/dev/null | head -1", 4);
      const masterOk = master.success && master.output.trim().length > 0;
      addRecord("ROS主节点", masterOk ? "运行正常" : "未运行或无话题", masterOk);

      const nodes = await api.rosExec("rosnode list 2>/dev/null", 4);
      const nodeCount = (nodes.output || "").split("\n").filter((l) => l.trim().length > 0).length;
      const nodesOk = nodes.success && nodeCount > 0;
      addRecord("ROS节点", nodesOk ? `${nodeCount} 个节点在线` : "无节点在线", nodesOk);

      const battery = await api.rosBattery();
      let batteryOk = true;
      let batteryStatus = "电量未知";
      const text = battery.battery?.trim();
      if (text && text.toLowerCase() !== "n/a") {
        const match = text.match(/([\d.]+)/);
        const value = match ? parseFloat(match[1]) : NaN;
        if (!isNaN(value)) {
          batteryOk = value >= 20;
          batteryStatus = batteryOk ? `电量 ${value}%` : `电量过低 ${value}%`;
        }
      }
      addRecord("电池电量", batteryStatus, batteryOk);
    } catch {
      addRecord("系统检查", "检查执行失败", false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">报警系统</h2>
        <SpringButton variant="primary" onClick={check} disabled={busy}>
          {busy ? "检查中..." : "🩺 立即检查"}
        </SpringButton>
      </div>

      <GlassCard className="p-6">
        <h3 className="font-semibold mb-3">报警记录</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-[--text-tertiary]">
              <th className="py-2 pr-4 font-medium">时间</th>
              <th className="py-2 pr-4 font-medium">项目</th>
              <th className="py-2 font-medium">状态</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => (
              <tr key={i} className="border-t border-black/5">
                <td className="py-2.5 pr-4 font-mono">{r.time}</td>
                <td className="py-2.5 pr-4">{r.item}</td>
                <td className="py-2.5">
                  <span
                    className="inline-flex items-center gap-1.5 font-medium"
                    style={{ color: r.ok ? GREEN : RED }}
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: r.ok ? GREEN : RED }}
                    />
                    {r.status}
                  </span>
                </td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr>
                <td colSpan={3} className="py-6 text-center text-sm text-[--text-tertiary]">
                  暂无报警记录,点击"立即检查"开始检查
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </GlassCard>
    </div>
  );
}
