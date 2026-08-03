import { useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

/** 摄像头画面页 */
export default function CameraViewPage() {
  const [topics, setTopics] = useState<string[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const detectTopics = async () => {
    setBusy(true);
    try {
      const res = await api.rosExec(
        'rostopic list 2>/dev/null | grep -iE "image|camera" | head -10',
        5
      );
      const list = (res.output || "")
        .split("\n")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);
      setTopics(list);
      if (list.length > 0) {
        setSelected(list[0]);
        setMsg(`检测到 ${list.length} 个图像话题`);
      } else {
        setMsg("未检测到图像话题,请确认相机驱动已启动");
      }
    } catch {
      setMsg("检测失败,请确认后端服务已启动");
    } finally {
      setBusy(false);
    }
  };

  const grabFrame = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const cmd = `rosrun image_view extract_images _sec_per_frame:=100 _filename_format:="/tmp/cam_frame.jpg" image:=${selected} __name:=gui_cam & sleep 2; pkill -f gui_cam; ls /tmp/cam_frame.jpg 2>/dev/null`;
      const res = await api.rosExec(cmd, 8);
      setMsg(res.success ? "画面抓取成功,已保存至 /tmp/cam_frame.jpg" : `抓取失败: ${res.error || "未知错误"}`);
    } catch {
      setMsg("抓取失败,请确认后端服务已启动");
    } finally {
      setBusy(false);
    }
  };

  const openViewer = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const res = await api.rosExec(`rosrun image_view image_view image:=${selected} &`, 3);
      setMsg(res.success ? "图像查看器已启动" : `启动失败: ${res.error || "未知错误"}`);
    } catch {
      setMsg("启动失败,请确认后端服务已启动");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <h2 className="text-xl font-bold">摄像头画面</h2>
      <p className="text-sm text-[--text-tertiary]">通过ROS话题显示图像</p>

      <GlassCard className="p-6">
        <div className="flex items-center gap-3">
          <SpringButton variant="secondary" onClick={detectTopics} disabled={busy}>
            {busy ? "检测中..." : "🔍 检测话题"}
          </SpringButton>
          {topics.length > 0 && <span className="text-sm text-[--text-tertiary]">已检测 {topics.length} 个话题</span>}
        </div>

        {topics.length > 0 && (
          <div className="mt-5 space-y-4">
            <div>
              <label className="text-sm text-[--text-secondary] block mb-1.5">选择话题</label>
              <select
                className="w-full bg-white/70 border border-black/10 rounded-xl px-3 py-2.5 text-sm font-mono outline-none focus:border-apple-blue"
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
              >
                {topics.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-3">
              <SpringButton variant="primary" onClick={grabFrame} disabled={busy}>
                📸 抓取画面
              </SpringButton>
              <SpringButton variant="secondary" onClick={openViewer} disabled={busy}>
                🖥 打开图像查看器
              </SpringButton>
            </div>
          </div>
        )}
      </GlassCard>

      <GlassCard className="p-6">
        <h3 className="font-semibold mb-2">说明</h3>
        <p className="text-sm text-[--text-secondary] leading-relaxed">
          浏览器版本暂不支持直接显示图像,请使用:
          <code className="ml-1 px-2 py-0.5 rounded-lg bg-white/70 text-xs font-mono">
            rosrun image_view image_view image:=话题
          </code>
        </p>
      </GlassCard>

      {topics.length > 0 && (
        <GlassCard className="p-6">
          <h3 className="font-semibold mb-3">检测到的话题 ({topics.length})</h3>
          <div className="max-h-72 overflow-y-auto space-y-1">
            {topics.map((t) => (
              <div
                key={t}
                className="flex items-center gap-2 p-2 rounded-lg bg-white/50 text-sm font-mono"
              >
                <span className="w-2 h-2 rounded-full bg-apple-purple" />
                {t}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {msg && <div className="text-sm text-[--text-secondary] px-1">{msg}</div>}
    </div>
  );
}
