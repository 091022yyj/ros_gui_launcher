import { motion } from "framer-motion";
import { useAnimationFrame, useFPS } from "../hooks/useAnimationFrame";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: "tasks", icon: "📋", label: "任务管理" },
  { id: "monitor", icon: "📊", label: "系统监控" },
  { id: "ros", icon: "🤖", label: "ROS监控" },
  { id: "terminal", icon: "💻", label: "终端" },
  { id: "logs", icon: "📝", label: "日志" },
  { id: "scenes", icon: "🎬", label: "场景管理" },
  { id: "settings", icon: "⚙️", label: "设置" },
];

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const fps = useFPS();

  return (
    <aside className="w-56 h-full glass flex flex-col p-4 m-3 mr-0">
      <div className="flex items-center gap-3 px-2 py-3 mb-4">
        <div className="w-9 h-9 rounded-xl bg-apple-blue flex items-center justify-center text-white text-lg shadow-lg">
          🤖
        </div>
        <div>
          <div className="font-bold text-[15px]">ROS 启动器</div>
          <div className="text-xs text-[--text-tertiary]">v3.6.11</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto">
        {tabs.map((tab) => (
          <motion.div
            key={tab.id}
            className={`nav-item ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => onTabChange(tab.id)}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </motion.div>
        ))}
      </nav>

      <div className="mt-4 px-2 py-2 rounded-xl bg-black/5 text-center">
        <div className="text-xs text-[--text-tertiary]">帧率 (自适应)</div>
        <div className="text-sm font-bold text-apple-blue">{fps} FPS</div>
      </div>
    </aside>
  );
}
