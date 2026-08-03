import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "./components/Sidebar";
import { waitForBackend } from "./hooks/useROS";
import { TaskList } from "./components/TaskList";
import { MonitorPage } from "./components/MonitorPage";
import { ROSMonitor } from "./components/ROSMonitor";
import RobotControl from "./components/RobotControl";
import NavigationPanel from "./components/NavigationPanel";
import SensorPanel from "./components/SensorPanel";
import CameraView from "./components/CameraView";
import TopicTable from "./components/TopicTable";
import TFView from "./components/TFView";
import BagManager from "./components/BagManager";
import Simulation from "./components/Simulation";
import TaskScheduler from "./components/TaskScheduler";
import AlarmSystem from "./components/AlarmSystem";
import MultiMachine from "./components/MultiMachine";
import DiskMonitor from "./components/DiskMonitor";
import LogAnalysis from "./components/LogAnalysis";
import SerialDebug from "./components/SerialDebug";
import { Terminal } from "./components/Terminal";
import { LogViewer } from "./components/LogViewer";
import { SceneManager } from "./components/SceneManager";
import Translator from "./components/Translator";
import { SettingsPage } from "./components/SettingsPage";

const pages: Record<string, React.ComponentType> = {
  tasks: TaskList,
  monitor: MonitorPage,
  ros: ROSMonitor,
  robot: RobotControl,
  navigation: NavigationPanel,
  sensors: SensorPanel,
  camera: CameraView,
  topics: TopicTable,
  tf: TFView,
  bags: BagManager,
  simulation: Simulation,
  scheduler: TaskScheduler,
  alarms: AlarmSystem,
  multi: MultiMachine,
  disk: DiskMonitor,
  analysis: LogAnalysis,
  serial: SerialDebug,
  terminal: Terminal,
  logs: LogViewer,
  scenes: SceneManager,
  translator: Translator,
  settings: SettingsPage,
};

export default function App() {
  const [activeTab, setActiveTab] = useState("tasks");
  const [backendReady, setBackendReady] = useState(false);
  const Page = pages[activeTab] || (() => <div>404</div>);

  // 等待Tauri自动启动的本地后端就绪
  useEffect(() => {
    waitForBackend().then(setBackendReady);
  }, []);

  if (!backendReady) {
    return (
      <div className="h-screen w-screen bg-apple-gray flex items-center justify-center">
        <div className="glass p-8 text-center">
          <div className="text-4xl mb-4 animate-pulse">🤖</div>
          <div className="font-semibold text-lg mb-1">ROS 启动器启动中</div>
          <div className="text-sm text-[--text-tertiary]">
            正在启动本地服务...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-apple-gray flex overflow-hidden">
      {/* 玻璃背景装饰 */}
      <div className="bg-blobs">
        <div className="blob w-96 h-96 bg-apple-blue/30 -top-20 -left-20" />
        <div className="blob w-80 h-80 bg-apple-purple/25 top-1/3 -right-20" style={{ animationDelay: "-7s" }} />
        <div className="blob w-72 h-72 bg-apple-green/20 bottom-0 left-1/3" style={{ animationDelay: "-14s" }} />
      </div>

      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 relative overflow-hidden p-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="h-full overflow-y-auto"
          >
            <Page />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
