import { useEffect, useState } from "react";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

/** ROS监控页 */
export function ROSMonitor() {
  const [nodes, setNodes] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const [n, t] = await Promise.all([api.rosNodes(), api.rosTopics()]);
      setNodes(n.nodes);
      setTopics(t.topics);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">ROS 监控</h2>
        <SpringButton variant="secondary" onClick={refresh} disabled={loading}>
          {loading ? "刷新中..." : "🔄 刷新"}
        </SpringButton>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <h3 className="font-semibold mb-3">ROS 节点 ({nodes.length})</h3>
          <div className="max-h-72 overflow-y-auto space-y-1">
            {nodes.map((node) => (
              <div
                key={node}
                className="flex items-center gap-2 p-2 rounded-lg bg-white/50 text-sm"
              >
                <span className="w-2 h-2 rounded-full bg-apple-green" />
                {node}
              </div>
            ))}
            {nodes.length === 0 && (
              <div className="text-sm text-[--text-tertiary] py-4 text-center">
                ROS主节点未运行或未发现节点
              </div>
            )}
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <h3 className="font-semibold mb-3">ROS 话题 ({topics.length})</h3>
          <div className="max-h-72 overflow-y-auto space-y-1">
            {topics.map((topic) => (
              <div
                key={topic}
                className="flex items-center gap-2 p-2 rounded-lg bg-white/50 text-sm font-mono"
              >
                <span className="w-2 h-2 rounded-full bg-apple-purple" />
                {topic}
              </div>
            ))}
            {topics.length === 0 && (
              <div className="text-sm text-[--text-tertiary] py-4 text-center">
                ROS主节点未运行或未发现话题
              </div>
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
