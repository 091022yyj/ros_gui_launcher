import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "./components/Sidebar";
import { TaskList } from "./components/TaskList";
import { MonitorPage } from "./components/MonitorPage";
import { ROSMonitor } from "./components/ROSMonitor";
import { Terminal } from "./components/Terminal";
import { LogViewer } from "./components/LogViewer";
import { SceneManager } from "./components/SceneManager";
import { SettingsPage } from "./components/SettingsPage";

const pages: Record<string, React.ComponentType> = {
  tasks: TaskList,
  monitor: MonitorPage,
  ros: ROSMonitor,
  terminal: Terminal,
  logs: LogViewer,
  scenes: SceneManager,
  settings: SettingsPage,
};

export default function App() {
  const [activeTab, setActiveTab] = useState("tasks");
  const Page = pages[activeTab] || (() => <div>404</div>);

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
