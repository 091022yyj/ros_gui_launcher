import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

type LogResultType = "dir" | "errors" | "detail";

interface LogResult {
  type: LogResultType;
  lines: string[];
}

const TITLES: Record<LogResultType, string> = {
  dir: "日志目录分析",
  errors: "包含 ERROR 的日志文件",
  detail: "ERROR 错误详情(最近)",
};

/** 日志分析页 */
export default function LogAnalysisPage() {
  const [result, setResult] = useState<LogResult | null>(null);
  const [busy, setBusy] = useState<LogResultType | null>(null);

  const run = async (type: LogResultType, cmd: string, timeout: number) => {
    setBusy(type);
    const res = await api.rosExec(cmd, timeout);
    setResult({
      type,
      lines: (res.output || res.error || "无输出").split("\n").filter((l) => l.length > 0),
    });
    setBusy(null);
  };

  const analyze = () =>
    run(
      "dir",
      'ls -la ~/.ros/log/ 2>/dev/null | head -15; echo "---"; find ~/.ros/log -name "*.log" -mmin -60 2>/dev/null | wc -l',
      6
    );

  const searchErrors = () =>
    run("errors", 'grep -rl "ERROR" ~/.ros/log/ 2>/dev/null | head -10', 6);

  const viewDetail = () =>
    run("detail", 'grep -h "ERROR" ~/.ros/log/latest/*.log 2>/dev/null | head -20', 6);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">日志分析</h2>
        <p className="text-sm text-[--text-tertiary] mt-1">
          检查 ~/.ros/log 目录下的日志,定位 ERROR 错误
        </p>
      </div>

      <GlassCard className="p-4">
        <div className="flex flex-wrap gap-2">
          <SpringButton onClick={analyze} disabled={busy !== null}>
            {busy === "dir" ? "分析中..." : "📊 分析日志"}
          </SpringButton>
          <SpringButton variant="secondary" onClick={searchErrors} disabled={busy !== null}>
            {busy === "errors" ? "搜索中..." : "🔍 搜索错误"}
          </SpringButton>
          <SpringButton variant="secondary" onClick={viewDetail} disabled={busy !== null}>
            {busy === "detail" ? "加载中..." : "📄 查看错误详情"}
          </SpringButton>
        </div>
      </GlassCard>

      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={result.type}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            <GlassCard className="p-4" strong>
              <h3 className="font-semibold text-[15px] mb-3">{TITLES[result.type]}</h3>
              {result.lines.length === 0 ? (
                <div className="text-sm text-[--text-tertiary] py-6 text-center">
                  未找到相关内容
                </div>
              ) : (
                <div className="rounded-xl bg-black/60 p-3 space-y-0.5 text-xs font-mono whitespace-pre-wrap break-all max-h-96 overflow-y-auto">
                  {result.lines.map((line, i) => {
                    const isError = line.includes("ERROR");
                    const isSep = line.trim() === "---";
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: Math.min(i * 0.02, 0.4) }}
                        className={
                          isError
                            ? "text-apple-red font-semibold"
                            : isSep
                              ? "text-[--text-tertiary] border-t border-white/10"
                              : line.includes("total") ||
                                  /^\d+\s+[\w-]+\s+\d+[\w.]+\s+\d{4}$/.test(line)
                                ? "text-[--text-tertiary]"
                                : "text-apple-green"
                        }
                      >
                        {line}
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
