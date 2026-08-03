import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api, Task } from "../hooks/useROS";

interface TaskItem {
  task: Task;
  status: "stopped" | "running" | "error";
}

/** 任务管理页 */
export function TaskList() {
  const [launchTasks, setLaunchTasks] = useState<TaskItem[]>([]);
  const [pyTasks, setPyTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadTasks = async () => {
    try {
      const { tasks } = await api.getTasks();
      setLaunchTasks(tasks.launch.map((t) => ({ task: t, status: "stopped" as const })));
      setPyTasks(tasks.py.map((t) => ({ task: t, status: "stopped" as const })));
    } catch (e) {
      console.error("加载任务失败:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const startTask = async (kind: "launch" | "py", item: TaskItem) => {
    const res = await api.startTask(kind, item.task);
    if (res.success) {
      if (kind === "launch") {
        setLaunchTasks((ts) =>
          ts.map((t) => (t.task.path === item.task.path ? { ...t, status: "running" } : t))
        );
      } else {
        setPyTasks((ts) =>
          ts.map((t) => (t.task.path === item.task.path ? { ...t, status: "running" } : t))
        );
      }
    }
  };

  const stopTask = async (kind: "launch" | "py", item: TaskItem) => {
    const res = await api.stopTask(item.task);
    if (res.success) {
      if (kind === "launch") {
        setLaunchTasks((ts) =>
          ts.map((t) => (t.task.path === item.task.path ? { ...t, status: "stopped" } : t))
        );
      } else {
        setPyTasks((ts) =>
          ts.map((t) => (t.task.path === item.task.path ? { ...t, status: "stopped" } : t))
        );
      }
    }
  };

  const TaskTable = ({ items, kind }: { items: TaskItem[]; kind: "launch" | "py" }) => (
    <GlassCard className="p-4">
      <h3 className="font-semibold text-[15px] mb-3">
        {kind === "launch" ? "Launch 文件" : "Python 文件"}
      </h3>
      {items.length === 0 ? (
        <div className="text-sm text-[--text-tertiary] py-8 text-center">
          暂无任务,请在后端配置中添加
        </div>
      ) : (
        <div className="space-y-2">
          <AnimatePresence>
            {items.map((item) => (
              <motion.div
                key={item.task.path}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
                className="flex items-center gap-3 p-3 rounded-xl bg-white/50 hover:bg-white/80 transition-colors"
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    item.status === "running" ? "bg-apple-green" : "bg-[--text-disabled]"
                  }`}
                />
                <span className="flex-1 text-sm truncate">{item.task.path}</span>
                {item.task.args && (
                  <span className="text-xs text-[--text-tertiary]">{item.task.args}</span>
                )}
                <span
                  className={`badge-${item.status === "running" ? "running" : "stopped"}`}
                >
                  {item.status === "running" ? "运行中" : "已停止"}
                </span>
                {item.status === "running" ? (
                  <SpringButton variant="danger" onClick={() => stopTask(kind, item)}>
                    停止
                  </SpringButton>
                ) : (
                  <SpringButton variant="primary" onClick={() => startTask(kind, item)}>
                    启动
                  </SpringButton>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </GlassCard>
  );

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">任务管理</h2>
        <SpringButton variant="secondary" onClick={loadTasks}>
          🔄 刷新
        </SpringButton>
      </div>
      {loading ? (
        <div className="text-center py-12 text-[--text-tertiary]">加载中...</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <TaskTable items={launchTasks} kind="launch" />
          <TaskTable items={pyTasks} kind="py" />
        </div>
      )}
    </div>
  );
}
