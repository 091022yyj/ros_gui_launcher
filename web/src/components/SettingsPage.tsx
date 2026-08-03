import { useEffect, useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api, Config } from "../hooks/useROS";

/** 设置页 */
export function SettingsPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getConfig().then(({ config }) => setConfig(config)).catch(() => {});
  }, []);

  if (!config) {
    return <div className="text-center py-12 text-[--text-tertiary]">加载中...</div>;
  }

  const save = async () => {
    const res = await api.saveConfig(config);
    if (res.success) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <h2 className="text-xl font-bold">设置</h2>

      <GlassCard className="p-6 space-y-4">
        <div>
          <label className="text-sm text-[--text-secondary] block mb-1.5">ROS setup 路径</label>
          <input
            className="w-full bg-white/70 border border-black/10 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-apple-blue"
            value={config.ros_setup}
            onChange={(e) => setConfig({ ...config, ros_setup: e.target.value })}
          />
        </div>
        <div>
          <label className="text-sm text-[--text-secondary] block mb-1.5">
            工作空间 setup 路径
          </label>
          <input
            className="w-full bg-white/70 border border-black/10 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-apple-blue"
            placeholder="留空自动探测 (如 ~/catkin_ws/devel/setup.bash)"
            value={config.ws_setup}
            onChange={(e) => setConfig({ ...config, ws_setup: e.target.value })}
          />
        </div>
        <div>
          <label className="text-sm text-[--text-secondary] block mb-1.5">顺序启动延时(秒)</label>
          <input
            type="number"
            className="w-32 bg-white/70 border border-black/10 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-apple-blue"
            value={config.start_delay}
            onChange={(e) => setConfig({ ...config, start_delay: Number(e.target.value) })}
          />
        </div>
        <SpringButton variant="primary" onClick={save}>
          {saved ? "✅ 已保存" : "💾 保存配置"}
        </SpringButton>
      </GlassCard>
    </div>
  );
}
