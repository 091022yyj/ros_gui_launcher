import { useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface SensorDef {
  name: string;
  icon: string;
  topics: string[];
}

const SENSORS: SensorDef[] = [
  { name: "激光雷达", icon: "📡", topics: ["/scan"] },
  { name: "IMU 惯性测量", icon: "🧭", topics: ["/imu"] },
  { name: "里程计", icon: "📍", topics: ["/odom"] },
  { name: "摄像头", icon: "📷", topics: ["/camera/image_raw", "/camera/image"] },
  { name: "电池", icon: "🔋", topics: ["/battery"] },
];

function isDetected(topics: string[], def: SensorDef): boolean {
  return topics.some((t) =>
    def.topics.some((p) => t === p || t.startsWith(p + "/"))
  );
}

export default function SensorPanelPage() {
  const [topics, setTopics] = useState<string[]>([]);
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [battery, setBattery] = useState<string | null>(null);
  const [batteryLoading, setBatteryLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    const res = await api.rosTopics().catch(() => ({ topics: [] as string[] }));
    setTopics(res.topics || []);
    setChecked(true);
    setLoading(false);
  }

  async function readBattery() {
    setBatteryLoading(true);
    const res = await api.rosBattery().catch(() => ({ battery: "" }));
    setBattery(res.battery || null);
    setBatteryLoading(false);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-5 max-w-3xl"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">传感器面板</h2>
        <SpringButton onClick={refresh} disabled={loading}>
          {loading ? "检测中…" : "刷新"}
        </SpringButton>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {SENSORS.map((sensor, i) => {
          const detected = isDetected(topics, sensor);
          return (
            <motion.div
              key={sensor.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <GlassCard className="p-5 text-center space-y-2">
                <div className="text-2xl">{sensor.icon}</div>
                <div className="font-medium">{sensor.name}</div>
                {checked ? (
                  detected ? (
                    <div className="text-apple-green font-semibold text-sm">
                      ✓ 正常
                    </div>
                  ) : (
                    <div className="text-apple-red font-semibold text-sm">
                      ✗ 未检测
                    </div>
                  )
                ) : (
                  <div className="text-[--text-tertiary] text-sm">
                    点击刷新检测
                  </div>
                )}
                <div className="text-xs text-[--text-tertiary] font-mono truncate">
                  {sensor.topics[0]}
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>

      <GlassCard className="p-5">
        <div className="flex items-center justify-between">
          <div className="font-medium">电池状态</div>
          <SpringButton
            variant="secondary"
            onClick={readBattery}
            disabled={batteryLoading}
          >
            {batteryLoading ? "读取中…" : "读取电池"}
          </SpringButton>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <div className="text-3xl">🔋</div>
          {battery !== null ? (
            <div className="flex-1">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-[--text-secondary]">当前电量</span>
                <span className="font-mono text-apple-green font-semibold">
                  {battery}
                </span>
              </div>
              <div className="h-2.5 rounded-full bg-black/10 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-apple-green"
                  initial={{ width: 0 }}
                  animate={{
                    width: `${Math.min(Math.max(parseFloat(battery) || 0, 0), 100)}%`,
                  }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          ) : (
            <div className="text-[--text-tertiary] text-sm">
              尚未读取电池信息
            </div>
          )}
        </div>
      </GlassCard>
    </motion.div>
  );
}
