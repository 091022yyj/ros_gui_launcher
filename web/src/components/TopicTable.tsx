import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface Field {
  key: string;
  value: string;
}

interface TopicData {
  topic: string;
  fields: Field[];
  error?: string;
}

const MAX_WATCH = 5;

function parseOutput(output: string): Field[] {
  const fields: Field[] = [];
  for (const line of output.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed === "---") continue;
    const m = trimmed.match(/^([\w\-]+):\s*(.*)$/);
    if (!m) continue;
    const key = m[1];
    const value = m[2].trim();
    if (!value || value.includes("{")) continue;
    fields.push({ key, value });
  }
  return fields;
}

export default function TopicTablePage() {
  const [available, setAvailable] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [watched, setWatched] = useState<string[]>([]);
  const [dataMap, setDataMap] = useState<Record<string, TopicData>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.rosTopics().then((res) => setAvailable(res.topics || [])).catch(() => {});
  }, []);

  async function fetchTopic(topic: string) {
    const res = await api
      .rosExec(`rostopic echo -n1 ${topic} 2>/dev/null | head -15`, 4)
      .catch(() => ({ success: false, output: "", error: "请求失败" }));
    setDataMap((prev) => ({
      ...prev,
      [topic]: res.success
        ? { topic, fields: parseOutput(res.output) }
        : { topic, fields: [], error: res.error || "获取失败" },
    }));
  }

  async function addWatch() {
    const topic = input.trim();
    if (!topic) return;
    if (watched.length >= MAX_WATCH) return;
    if (watched.includes(topic)) {
      setInput("");
      return;
    }
    setWatched((prev) => [...prev, topic]);
    setInput("");
    setLoading(true);
    await fetchTopic(topic);
    setLoading(false);
  }

  async function refreshAll() {
    if (watched.length === 0) return;
    setLoading(true);
    await Promise.all(watched.map((t) => fetchTopic(t)));
    setLoading(false);
  }

  function clearAll() {
    setWatched([]);
    setDataMap({});
    setInput("");
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-5"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">话题数据表</h2>
        <div className="flex gap-2">
          <SpringButton variant="secondary" onClick={refreshAll} disabled={loading || watched.length === 0}>
            {loading ? "刷新中…" : "刷新"}
          </SpringButton>
          <SpringButton variant="secondary" onClick={clearAll} disabled={watched.length === 0}>
            清空
          </SpringButton>
        </div>
      </div>

      <GlassCard className="p-5">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              list="topic-options"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addWatch()}
              placeholder="选择或输入要监控的话题"
              className="w-full px-4 py-2.5 rounded-xl bg-white/60 border border-black/5 text-sm outline-none focus:ring-2 focus:ring-apple-blue/40 placeholder-[--text-tertiary]"
            />
            <datalist id="topic-options">
              {available.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </div>
          <SpringButton onClick={addWatch} disabled={watched.length >= MAX_WATCH}>
            添加监控
          </SpringButton>
        </div>
        <div className="mt-2 text-xs text-[--text-tertiary] flex items-center justify-between">
          <span>
            监控中 {watched.length} / {MAX_WATCH}
          </span>
          {watched.length >= MAX_WATCH && <span>已达监控上限</span>}
        </div>
      </GlassCard>

      <GlassCard className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[--text-tertiary] text-xs border-b border-black/5 bg-black/[0.02]">
              <th className="px-5 py-3 font-medium w-48">话题</th>
              <th className="px-5 py-3 font-medium w-40">字段</th>
              <th className="px-5 py-3 font-medium">值</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {watched.map((topic) => {
                const data = dataMap[topic];
                const fields = data?.fields || [];
                const error = data?.error;
                return (
                  <motion.tbody
                    key={topic}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="border-b border-black/5 last:border-0"
                  >
                    {error ? (
                      <tr>
                        <td colSpan={3} className="px-5 py-3 text-apple-red text-xs">
                          {topic}：{error}
                        </td>
                      </tr>
                    ) : fields.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-5 py-3 text-[--text-tertiary] text-xs">
                          {topic}：暂无数据
                        </td>
                      </tr>
                    ) : (
                      fields.map((f, i) => (
                        <tr key={`${topic}-${i}`}>
                          {i === 0 && (
                            <td
                              rowSpan={fields.length}
                              className="px-5 py-3 font-mono text-xs text-apple-blue align-top break-all"
                            >
                              {topic}
                            </td>
                          )}
                          <td className="px-5 py-1.5 font-mono text-xs text-[--text-secondary] align-top break-all">
                            {f.key}
                          </td>
                          <td className="px-5 py-1.5 font-mono text-xs align-top break-all">
                            {f.value}
                          </td>
                        </tr>
                      ))
                    )}
                  </motion.tbody>
                );
              })}
            </AnimatePresence>
            {watched.length === 0 && (
              <tr>
                <td colSpan={3} className="px-5 py-8 text-center text-[--text-tertiary] text-sm">
                  尚未添加监控话题
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </GlassCard>
    </motion.div>
  );
}
