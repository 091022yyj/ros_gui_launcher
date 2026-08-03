import { useEffect, useRef, useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

const BAUDS = ["9600", "57600", "115200"];

/** 串口调试页 */
export default function SerialDebugPage() {
  const [ports, setPorts] = useState<string[]>([]);
  const [selectedPort, setSelectedPort] = useState("");
  const [baud, setBaud] = useState("115200");
  const [open, setOpen] = useState(false);
  const [scanMsg, setScanMsg] = useState("尚未扫描,请点击扫描端口");
  const [needsPyserial, setNeedsPyserial] = useState(false);
  const [rx, setRx] = useState<string[]>([]);
  const [tx, setTx] = useState("");
  const rxRef = useRef<string[]>([]);
  const logRef = useRef<HTMLTextAreaElement>(null);

  const appendRx = (line: string) => {
    rxRef.current = [...rxRef.current, line].slice(-300);
    setRx(rxRef.current);
  };

  const scanPorts = async () => {
    setScanMsg("扫描中...");
    const res = await api.rosExec("ls /dev/ttyUSB* /dev/ttyACM* /dev/ttyS* 2>/dev/null", 4);
    const output = (res.output || "").trim();
    if (res.success && output) {
      const list = output.split("\n").filter((l) => l.trim().length > 0);
      setPorts(list);
      setSelectedPort((p) => p || list[0] || "");
      setScanMsg(`发现 ${list.length} 个串口设备`);
      setNeedsPyserial(false);
    } else {
      setPorts([]);
      setSelectedPort("");
      setScanMsg("未检测到串口设备,请确认已连接并安装 pyserial");
      setNeedsPyserial(true);
    }
  };

  const togglePort = () => {
    if (open) {
      setOpen(false);
      appendRx(`[系统] 串口已关闭 (${selectedPort})`);
    } else {
      setOpen(true);
      appendRx(`[系统] 已连接 ${selectedPort || "(未选择)"} @ ${baud} baud`);
    }
  };

  const send = () => {
    const cmd = tx.trim();
    if (!cmd || !open) return;
    appendRx(`发送 >>> ${cmd}`);
    setTx("");
  };

  useEffect(() => {
    if (!open) return;
    const timer = setInterval(() => {
      const ts = new Date().toLocaleTimeString("zh-CN", { hour12: false });
      const hex = Math.floor(Math.random() * 256)
        .toString(16)
        .toUpperCase()
        .padStart(2, "0");
      appendRx(`[${ts}] 模拟数据: ${hex} (串口数据接收需要后端WebSocket支持)`);
    }, 1500);
    return () => clearInterval(timer);
  }, [open]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [rx]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">串口调试</h2>
        <p className="text-sm text-[--text-tertiary] mt-1">
          通过串口连接调试底盘(需后端支持pyserial)
        </p>
      </div>

      {needsPyserial && (
        <GlassCard className="p-4 bg-apple-red/15">
          <p className="text-sm text-apple-red font-medium">⚠ 请安装: pip install pyserial</p>
        </GlassCard>
      )}

      <GlassCard className="p-4">
        <div className="flex flex-wrap items-end gap-3 mb-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[--text-tertiary]">串口设备</label>
            <select
              className="px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm min-w-40"
              value={selectedPort}
              onChange={(e) => setSelectedPort(e.target.value)}
            >
              {ports.length === 0 && <option value="">未发现端口</option>}
              {ports.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[--text-tertiary]">波特率</label>
            <select
              className="px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm"
              value={baud}
              onChange={(e) => setBaud(e.target.value)}
            >
              {BAUDS.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>
          <SpringButton variant="secondary" onClick={scanPorts}>
            🔍 扫描端口
          </SpringButton>
          <SpringButton variant={open ? "danger" : "primary"} onClick={togglePort}>
            {open ? "🔴 关闭串口" : "🟢 打开串口"}
          </SpringButton>
        </div>
        <p className="text-xs text-[--text-tertiary]">{scanMsg}</p>
      </GlassCard>

      <GlassCard className="p-4" strong>
        <h3 className="font-semibold text-[15px] mb-3">接收区</h3>
        <textarea
          ref={logRef}
          readOnly
          value={rx.join("\n")}
          className="w-full h-48 rounded-xl bg-black/60 text-apple-green text-xs font-mono p-3 resize-none focus:outline-none"
          placeholder="串口数据接收需要后端WebSocket支持,当前显示模拟数据"
        />
      </GlassCard>

      <GlassCard className="p-4">
        <h3 className="font-semibold text-[15px] mb-3">发送区</h3>
        <div className="flex gap-2">
          <input
            className="flex-1 px-3 py-2 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:ring-2 focus:ring-apple-blue/60 text-sm font-mono"
            placeholder="输入要发送的指令"
            value={tx}
            onChange={(e) => setTx(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <SpringButton onClick={send} disabled={!tx.trim() || !open}>
            📤 发送
          </SpringButton>
        </div>
      </GlassCard>
    </div>
  );
}
