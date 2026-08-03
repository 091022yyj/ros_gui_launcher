import { useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";

interface TranslationRule {
  keyword: string;
  explain: string;
}

const DICT: TranslationRule[] = [
  { keyword: "resource not found", explain: "找不到资源（文件、配置或资源路径不存在，检查路径拼写与文件是否就位）" },
  { keyword: "unable to communicate with master", explain: "无法与主节点通信（roscore 未启动或网络不通，请先启动 roscore）" },
  { keyword: "connection refused", explain: "连接被拒绝（目标端口未监听，服务未启动或 IP/端口配置错误）" },
  { keyword: "package not found", explain: "找不到功能包（未 source 工作空间，或功能包未编译/未安装）" },
  { keyword: "command not found", explain: "命令不存在（未安装对应工具，或未加载环境变量）" },
  { keyword: "permission denied", explain: "权限不足（当前用户无权访问该文件或设备，检查权限或用 sudo）" },
  { keyword: "no such file", explain: "没有此文件（路径不存在或文件名拼写错误）" },
  { keyword: "spawn service not available", explain: "生成服务不可用（Gazebo 未启动或 spawn 服务未就绪，请先启动仿真）" },
  { keyword: "process has died", explain: "进程已终止（节点崩溃退出，查看日志确认崩溃原因）" },
  { keyword: "failed to load", explain: "加载失败（文件加载出错，检查格式、编码与路径）" },
  { keyword: "timed out", explain: "超时（等待服务或通信响应超时，网络延迟或目标未响应）" },
  { keyword: "timeout", explain: "超时（操作在规定时间内未完成，可增大超时时间）" },
  { keyword: "unknown error", explain: "未知错误（未识别的异常，请提供完整错误上下文以便排查）" },
  { keyword: "address already in use", explain: "端口已被占用（上次进程未退出，用 ps / kill 清理或更换端口）" },
  { keyword: "no ros master", explain: "ROS 主节点未运行（请先启动 roscore，或检查 ROS_MASTER_URI）" },
  { keyword: "cannot open file", explain: "无法打开文件（文件不存在或没有读取权限）" },
  { keyword: "segmentation fault", explain: "段错误（程序访问了非法内存，通常是 C/C++ 指针或数组越界问题）" },
  { keyword: "invalid argument", explain: "参数无效（传入的参数类型或数值不合法，检查参数格式）" },
  { keyword: "bad_alloc", explain: "内存分配失败（内存不足，释放资源或减少数据量）" },
  { keyword: "nameerror", explain: "未定义变量（Python 中引用了未定义的名称，检查变量名拼写）" },
];

function translate(input: string): TranslationRule[] {
  const lower = input.toLowerCase();
  return DICT.filter((r) => lower.includes(r.keyword));
}

export default function TranslatorPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<TranslationRule[] | null>(null);

  function handleTranslate() {
    setResult(translate(text));
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-5 max-w-2xl"
    >
      <h2 className="text-xl font-bold">报错翻译</h2>

      <GlassCard className="space-y-4">
        <p className="text-sm text-[--text-secondary]">
          输入ROS错误信息，翻译为中文解释
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例如：Resource not found: /home/user/xx.launch"
          rows={5}
          className="w-full px-4 py-3 rounded-xl border border-black/5 bg-white/60
            font-mono text-sm resize-y
            focus:outline-none focus:ring-2 focus:ring-apple-blue/40"
        />
        <div className="flex gap-3">
          <SpringButton
            className="px-8 py-3 font-bold"
            onClick={handleTranslate}
            disabled={!text.trim()}
          >
            翻译
          </SpringButton>
        </div>

        {result !== null && (
          <GlassCard strong className="space-y-3 p-5">
            {result.length > 0 ? (
              result.map((r) => (
                <div key={r.keyword} className="space-y-1">
                  <div className="text-xs font-mono text-apple-blue">
                    ✓ {r.keyword}
                  </div>
                  <div className="text-sm">{r.explain}</div>
                </div>
              ))
            ) : (
              <p className="text-sm text-[--text-tertiary]">未找到对应解释</p>
            )}
          </GlassCard>
        )}
      </GlassCard>
    </motion.div>
  );
}
