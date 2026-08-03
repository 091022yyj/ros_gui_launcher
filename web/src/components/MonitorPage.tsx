import { useEffect, useState } from "react";
import { GlassCard } from "./GlassCard";
import { RealtimeChart } from "./RealtimeChart";
import { api } from "../hooks/useROS";

/** 系统监控页 */
export function MonitorPage() {
  const [info, setInfo] = useState({ cpu: 0, memory: 0, disk: 0, hostname: "" });

  useEffect(() => {
    api.systemInfo().then(setInfo).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">系统监控</h2>

      <div className="grid grid-cols-3 gap-4">
        <GlassCard className="p-4 text-center">
          <div className="text-xs text-[--text-tertiary]">主机名</div>
          <div className="text-lg font-bold mt-1">{info.hostname || "--"}</div>
        </GlassCard>
        <GlassCard className="p-4 text-center">
          <div className="text-xs text-[--text-tertiary]">内存</div>
          <div className="text-lg font-bold mt-1 text-apple-blue">{info.memory}%</div>
        </GlassCard>
        <GlassCard className="p-4 text-center">
          <div className="text-xs text-[--text-tertiary]">磁盘</div>
          <div className="text-lg font-bold mt-1 text-apple-orange">{info.disk}%</div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <RealtimeChart color="#0071e3" label="CPU 使用率" />
        <RealtimeChart color="#34c759" label="内存使用率" />
      </div>
    </div>
  );
}
