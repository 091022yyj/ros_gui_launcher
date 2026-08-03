import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface ScheduleTask {
  id: string;
  name: string;
  interval: number;
  enabled: boolean;
}

const STORAGE_KEY = "task_scheduler_tasks";

function loadTasks(): ScheduleTask[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ScheduleTask[]) : [];
  } catch {
    return [];
  }
}

function saveTasks(tasks: ScheduleTask[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

/** 任务调度页 */
export default function TaskSchedulerPage() {
  const [tasks, setTasks] = useState<ScheduleTask[]>([]);
  const [name, setName] = useState("");
  const [interval, setIntervalStr] = useState("60");
  const [schedulesFile, setSchedulesFile] = useState("");

  useEffect(() => {
    setTasks(loadTasks());
    api.rosExec("ls ~/schedules.json 2>/dev/null && cat ~/schedules.json", 3)
      .then((res) => {
        if (res.success && res.output.trim()) {
          setSchedulesFile(res.output.trim());
        }
      })
      .catch(() => {});
  }, []);

  const persist = (next: ScheduleTask[]) => {
    setTasks(next);
    saveTasks(next);
  };

  const addTask = () => {
    const trimmed = name.trim();
    const secs = Math.max(1, Number(interval) || 0);
    if (!trimmed || secs <= 0) return;
    const task: ScheduleTask = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: trimmed,
      interval: secs,
      enabled: true,
    };
    persist([...tasks, task]);
    setName("");
    setIntervalStr("60");
  };

  const toggleTask = (id: string) => {
    persist(tasks.map((t) => (t.id === id ? { ...t, enabled: !t.enabled } : t)));
  };

  const removeTask = (id: string) => {
    persist(tasks.filter((t) => t.id !== id));
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">任务调度</h2>

      <GlassCard className="p-4">
        <h3 className="font-semibold text-[15px] mb-3">添加定时任务</h3>
        <div className="flex gap-2">
          <input
            className="flex-1 px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
            placeholder="任务名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addTask()}
          />
          <input
            className="w-28 px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
            type="number"
            min={1}
            placeholder="间隔秒数"
            value={interval}
            onChange={(e) => setIntervalStr(e.target.value)}
          />
          <SpringButton onClick={addTask} disabled={!name.trim()}>
            ➕ 添加任务
          </SpringButton>
        </div>
      </GlassCard>

      <GlassCard className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-[15px]">定时任务</h3>
          <span className="text-xs text-[--text-tertiary]">共 {tasks.length} 个</span>
        </div>
        {tasks.length === 0 ? (
          <div className="text-sm text-[--text-tertiary] py-8 text-center">
            暂无定时任务,请在上方添加
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {tasks.map((task) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  className="flex items-center gap-3 p-3 rounded-xl bg-white/50 hover:bg-white/80 transition-colors"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      task.enabled ? "bg-apple-green" : "bg-[--text-disabled]"
                    }`}
                  />
                  <span className="flex-1 text-sm truncate">{task.name}</span>
                  <span className="text-xs text-[--text-tertiary]">
                    每 {task.interval} 秒
                  </span>
                  <span className={`badge-${task.enabled ? "running" : "stopped"}`}>
                    {task.enabled ? "启用" : "禁用"}
                  </span>
                  <SpringButton variant="secondary" onClick={() => toggleTask(task.id)}>
                    {task.enabled ? "禁用" : "启用"}
                  </SpringButton>
                  <SpringButton variant="danger" onClick={() => removeTask(task.id)}>
                    删除
                  </SpringButton>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </GlassCard>

      {schedulesFile && (
        <GlassCard className="p-4">
          <h3 className="font-semibold text-[15px] mb-3">~/schedules.json</h3>
          <pre className="text-xs whitespace-pre-wrap break-all bg-white/40 rounded-xl p-3">
            {schedulesFile}
          </pre>
        </GlassCard>
      )}
    </div>
  );
}
