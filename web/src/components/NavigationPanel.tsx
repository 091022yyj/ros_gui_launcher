import { useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

function buildNavCmd(x: number, y: number): string {
  return `python3 -c 'import math, rospy, actionlib; from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal; rospy.init_node("gui_nav"); c=actionlib.SimpleActionClient("move_base", MoveBaseAction); print("OK" if c.wait_for_server(rospy.Duration(5)) else "NO_SERVER"); g=MoveBaseGoal(); g.target_pose.header.frame_id="map"; g.target_pose.pose.position.x=${x}; g.target_pose.pose.position.y=${y}; g.target_pose.pose.orientation.w=1; c.send_goal(g); c.wait_for_result(rospy.Duration(15)); print("SUCCESS" if c.get_state()==3 else "FAILED")'`;
}

export default function NavigationPanelPage() {
  const [x, setX] = useState(2);
  const [y, setY] = useState(0);
  const [heading, setHeading] = useState(0);
  const [output, setOutput] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendGoal() {
    if (busy) return;
    setBusy(true);
    setOutput("正在发送目标…");
    const res = await api.rosExec(buildNavCmd(x, y), 40).catch(() => ({
      success: false,
      output: "",
      error: "请求失败",
    }));
    setBusy(false);
    if (res.error) {
      setOutput(`执行出错：${res.error}\n${res.output}`);
    } else {
      setOutput(res.output);
    }
  }

  async function cancelGoal() {
    if (busy) return;
    setBusy(true);
    const res = await api.rosExec(
      'rostopic pub -1 /move_base/cancel actionlib_msgs/GoalID "{}"',
      3
    ).catch(() => ({ success: false, output: "", error: "请求失败" }));
    setBusy(false);
    setOutput(res.error ? `取消失败：${res.error}` : "已发送取消指令");
  }

  const success = /SUCCESS/.test(output);
  const failed = /FAILED|NO_SERVER/.test(output);
  const running = output.includes("正在发送") || output.includes("等待");

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-5 max-w-2xl"
    >
      <h2 className="text-xl font-bold">一键导航</h2>

      <GlassCard className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "X (米)", value: x, set: setX },
            { label: "Y (米)", value: y, set: setY },
            { label: "朝向 (度)", value: heading, set: setHeading },
          ].map((f) => (
            <div key={f.label}>
              <label className="text-sm text-[--text-secondary] block mb-1">
                {f.label}
              </label>
              <input
                type="number"
                step="0.1"
                value={f.value}
                onChange={(e) => f.set(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl border border-black/5 bg-white/60
                  focus:outline-none focus:ring-2 focus:ring-apple-blue/40"
              />
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <SpringButton
            className="flex-1 py-3 text-base font-bold"
            onClick={sendGoal}
            disabled={busy}
          >
            发送目标
          </SpringButton>
          <SpringButton
            variant="secondary"
            className="flex-1 py-3 text-base font-bold"
            onClick={cancelGoal}
            disabled={busy}
          >
            取消目标
          </SpringButton>
        </div>

        <motion.div
          animate={{ opacity: running ? 0.7 : 1 }}
          className={`rounded-xl px-4 py-3 font-mono text-sm whitespace-pre-wrap min-h-16 max-h-48 overflow-y-auto ${
            success
              ? "bg-apple-green/10 text-apple-green"
              : failed
                ? "bg-apple-red/10 text-apple-red"
                : "bg-black/5 text-[--text-secondary]"
          }`}
        >
          {output || "等待发送目标…"}
        </motion.div>
      </GlassCard>
    </motion.div>
  );
}
