import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface Machine {
  name: string;
  host: string;
  user: string;
  port: string;
}

interface TestResult {
  ok: boolean;
  msg: string;
}

interface CmdResult {
  ok: boolean;
  text: string;
}

const MACHINES_KEY = "machines";

/** 多机协同(SSH远程控制) */
export default function MultiMachinePage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [user, setUser] = useState("");
  const [port, setPort] = useState("22");
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [commands, setCommands] = useState<Record<string, string>>({});
  const [outputs, setOutputs] = useState<Record<string, CmdResult>>({});
  const [testingId, setTestingId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(MACHINES_KEY);
      if (saved) setMachines(JSON.parse(saved));
    } catch {
      /* 忽略损坏数据 */
    }
  }, []);

  const persist = (list: Machine[]) => {
    setMachines(list);
    localStorage.setItem(MACHINES_KEY, JSON.stringify(list));
  };

  const keyOf = (m: Machine) => `${m.user}@${m.host}:${m.port}`;

  const addMachine = () => {
    if (!name.trim() || !host.trim() || !user.trim()) return;
    const m: Machine = {
      name: name.trim(),
      host: host.trim(),
      user: user.trim(),
      port: port.trim() || "22",
    };
    persist([...machines, m]);
    setName("");
    setHost("");
    setUser("");
    setPort("22");
  };

  const removeMachine = (m: Machine) => {
    persist(machines.filter((x) => keyOf(x) !== keyOf(m)));
    const id = keyOf(m);
    setTestResults((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setOutputs((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const testConnection = async (m: Machine) => {
    const id = keyOf(m);
    setTestingId(id);
    setTestResults((prev) => ({ ...prev, [id]: { ok: true, msg: "测试中..." } }));
    const res = await api.rosExec(
      `ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p ${m.port} ${m.user}@${m.host} "echo connected"`,
      8
    );
    if (testingId === id) setTestingId(null);
    const connected = res.success && res.output.includes("connected");
    setTestResults((prev) => ({
      ...prev,
      [id]: connected
        ? { ok: true, msg: "✓ 连接成功" }
        : { ok: false, msg: `✗ 失败: ${res.error ?? (res.output || "连接超时")}` },
    }));
  };

  const execCommand = async (m: Machine) => {
    const cmd = (commands[keyOf(m)] ?? "").trim();
    if (!cmd) return;
    const id = keyOf(m);
    setOutputs((prev) => ({ ...prev, [id]: { ok: true, text: "执行中..." } }));
    const escaped = cmd.replace(/"/g, '\\"');
    const res = await api.rosExec(
      `ssh -o ConnectTimeout=5 -p ${m.port} ${m.user}@${m.host} "${escaped}"`,
      10
    );
    setOutputs((prev) => ({
      ...prev,
      [id]: res.success
        ? { ok: true, text: res.output.trim() || "(命令已执行,无输出)" }
        : { ok: false, text: res.error ?? "执行失败" },
    }));
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">多机协同</h2>
        <p className="text-sm text-[--text-tertiary] mt-1">
          通过SSH控制远程机器上的ROS系统
        </p>
      </div>

      <GlassCard className="p-4">
        <h3 className="font-semibold text-[15px] mb-3">添加机器</h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 mb-3">
          <input
            className="px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
            placeholder="机器名"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
            placeholder="主机名/IP"
            value={host}
            onChange={(e) => setHost(e.target.value)}
          />
          <input
            className="px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
            placeholder="用户名"
            value={user}
            onChange={(e) => setUser(e.target.value)}
          />
          <input
            className="px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
            placeholder="端口(默认22)"
            value={port}
            onChange={(e) => setPort(e.target.value.replace(/[^\d]/g, ""))}
          />
        </div>
        <SpringButton onClick={addMachine} disabled={!name.trim() || !host.trim() || !user.trim()}>
          ➕ 添加
        </SpringButton>
        {machines.length > 0 && (
          <span className="ml-3 text-xs text-[--text-tertiary]">已保存 {machines.length} 台机器</span>
        )}
      </GlassCard>

      {machines.length === 0 ? (
        <GlassCard className="p-4 text-center text-sm text-[--text-tertiary] py-8">
          暂无机器,请先添加
        </GlassCard>
      ) : (
        <AnimatePresence>
          {machines.map((m) => {
            const id = keyOf(m);
            const test = testResults[id];
            const out = outputs[id];
            return (
              <motion.div
                key={id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              >
                <GlassCard className="p-4" strong>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-apple-green" />
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-[15px] truncate">{m.name}</div>
                      <div className="text-xs text-[--text-tertiary] truncate">
                        {m.user}@{m.host}:{m.port}
                      </div>
                    </div>
                    <SpringButton
                      variant="secondary"
                      onClick={() => testConnection(m)}
                      disabled={testingId === id}
                    >
                      {testingId === id ? "测试中..." : "🧪 测试连接"}
                    </SpringButton>
                    <SpringButton variant="danger" onClick={() => removeMachine(m)}>
                      🗑 删除
                    </SpringButton>
                  </div>

                  {test && (
                    <div
                      className={`text-xs mb-3 px-3 py-1.5 rounded-lg ${
                        test.ok ? "bg-apple-green/20 text-apple-green" : "bg-apple-red/20 text-apple-red"
                      }`}
                    >
                      {test.msg}
                    </div>
                  )}

                  <div className="flex gap-2">
                    <input
                      className="flex-1 px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm font-mono"
                      placeholder="输入远程命令,如: rosnode list"
                      value={commands[id] ?? ""}
                      onChange={(e) => setCommands((prev) => ({ ...prev, [id]: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && execCommand(m)}
                    />
                    <SpringButton onClick={() => execCommand(m)} disabled={!(commands[id] ?? "").trim()}>
                      ▶ 执行命令
                    </SpringButton>
                  </div>

                  {out && (
                    <pre
                      className={`mt-3 p-3 rounded-xl text-xs font-mono whitespace-pre-wrap break-all bg-black/60 text-apple-green ${
                        out.ok ? "" : "text-apple-red"
                      }`}
                    >
                      {out.text}
                    </pre>
                  )}
                </GlassCard>
              </motion.div>
            );
          })}
        </AnimatePresence>
      )}
    </div>
  );
}
