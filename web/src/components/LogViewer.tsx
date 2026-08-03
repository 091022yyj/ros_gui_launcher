import { GlassCard } from "./GlassCard";

/** 日志页 */
export function LogViewer() {
  const logs = [
    "[10:00:01] 正在检查更新...",
    "[10:00:02] 当前已是最新版本 (v3.6.11)",
    "[10:00:05] >>> 启动: /home/ub/catkin_ws/src/wpr_simulation/launch/wpb_gmapping.launch",
    "[10:00:08] [wpb_gmapping.launch] process started",
    "[10:00:10] [wpb_gmapping.launch] [INFO] Gmapping node started",
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">运行日志</h2>
      <GlassCard className="p-4 !bg-black/80">
        <div className="h-[calc(100vh-180px)] overflow-y-auto font-mono text-xs space-y-0.5">
          {logs.map((line, i) => (
            <div
              key={i}
              className={line.includes("ERROR") || line.includes("失败")
                ? "text-red-400"
                : line.includes(">>>") || line.includes("started")
                ? "text-green-400"
                : "text-gray-300"}
            >
              {line}
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
