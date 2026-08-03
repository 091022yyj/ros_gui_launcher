import { motion } from "framer-motion";
import { useFPS } from "../hooks/useAnimationFrame";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const TABS = [
  { id: "tasks", icon: "📋", label: "任务管理" },
  { id: "monitor", icon: "📊", label: "系统监控" },
  { id: "ros", icon: "🤖", label: "ROS监控" },
  { id: "robot", icon: "🎮", label: "遥控面板" },
  { id: "navigation", icon: "🧭", label: "一键导航" },
  { id: "sensors", icon: "📡", label: "传感器面板" },
  { id: "camera", icon: "📷", label: "摄像头" },
  { id: "topics", icon: "📊", label: "话题数据表" },
  { id: "tf", icon: "🕸️", label: "TF坐标系" },
  { id: "bags", icon: "📼", label: "rosbag管理" },
  { id: "simulation", icon: "🎛️", label: "仿真控制" },
  { id: "scheduler", icon: "⏰", label: "任务调度" },
  { id: "alarms", icon: "🔔", label: "报警系统" },
  { id: "multi", icon: "🌍", label: "多机协同" },
  { id: "disk", icon: "💾", label: "磁盘监控" },
  { id: "analysis", icon: "🔍", label: "日志分析" },
  { id: "serial", icon: "🔌", label: "串口调试" },
  { id: "terminal", icon: "💻", label: "终端" },
  { id: "logs", icon: "📝", label: "日志" },
  { id: "scenes", icon: "🎬", label: "场景管理" },
  { id: "translator", icon: "🌐", label: "报错翻译" },
  { id: "settings", icon: "⚙️", label: "设置" },
];

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const fps = useFPS();

  return (
    <aside className="w-52 h-full glass flex flex-col p-3 m-3 mr-0">
      <div className="flex items-center gap-2.5 px-2 py-2.5 mb-3">
        <div className="w-9 h-9 rounded-xl bg-apple-blue flex items-center justify-center text-white text-lg shadow-lg">
          🤖
        </div>
        <div>
          <div className="font-bold text-[15px]">ROS 启动器</div>
          <div className="text-xs text-[--text-tertiary]">v3.6.11</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto pr-0.5">
        {TABS.map((tab) => (
          <motion.div
            key={tab.id}
            className={`nav-item !px-3 !py-2 !text-[13px] ${
              activeTab === tab.id ? "active" : ""
            }`}
            onClick={() => onTabChange(tab.id)}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
          >
            <span className="text-sm">{tab.icon}</span>
            <span className="truncate">{tab.label}</span>
          </motion.div>
        ))}
      </nav>

      <div className="mt-3 px-2 py-2 rounded-xl bg-black/5 text-center">
        <div className="text-xs text-[--text-tertiary]">帧率 (自适应)</div>
        <div className="text-sm font-bold text-apple-blue">{fps} FPS</div>
      </div>
    </aside>
  );
}
