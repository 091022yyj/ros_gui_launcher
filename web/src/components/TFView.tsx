import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";
import { api } from "../hooks/useROS";

interface TFNode {
  parent: string;
  child: string;
}

const COLORS = ["bg-apple-green", "bg-apple-blue", "bg-apple-purple", "bg-apple-orange", "bg-apple-red", "bg-apple-teal"];

/** TF 坐标树节点 */
function TFTreeNode({
  name,
  childrenMap,
  depth,
}: {
  name: string;
  childrenMap: Map<string, TFNode[]>;
  depth: number;
}) {
  const children = childrenMap.get(name) ?? [];
  const color = COLORS[depth % COLORS.length];
  return (
    <div className="space-y-1">
      <motion.div
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: "spring", stiffness: 400, damping: 30 }}
        className="flex items-center gap-2 py-1"
        style={{ marginLeft: depth * 20 }}
      >
        {depth > 0 && (
          <span className="text-[--text-disabled] select-none">└─</span>
        )}
        <span className={`w-2 h-2 rounded-full ${color}`} />
        <span className="text-sm">{name}</span>
        <span className="text-xs text-[--text-tertiary]">
          父级: {depth > 0 ? "见上方" : "根"}
        </span>
      </motion.div>
      {children.length > 0 && (
        <div className="space-y-1">
          {children.map((n) => (
            <TFTreeNode key={n.child} name={n.child} childrenMap={childrenMap} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

/** TF 坐标系页 */
export default function TFViewPage() {
  const [transforms, setTransforms] = useState<TFNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { roots, childrenMap } = useMemo(() => {
    const map = new Map<string, TFNode[]>();
    const childSet = new Set<string>();
    for (const t of transforms) {
      childSet.add(t.child);
      const list = map.get(t.parent) ?? [];
      list.push(t);
      map.set(t.parent, list);
    }
    const roots = Array.from(map.keys()).filter((p) => !childSet.has(p));
    return { roots, childrenMap: map };
  }, [transforms]);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.rosTF();
      if (res.error) {
        setError(res.error);
      } else {
        setTransforms(res.transforms ?? []);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">TF坐标系</h2>
        <SpringButton variant="secondary" onClick={load} disabled={loading}>
          {loading ? "刷新中..." : "🔄 刷新"}
        </SpringButton>
      </div>

      {error && (
        <GlassCard className="p-3 text-sm text-[--text-danger]">
          {error}
        </GlassCard>
      )}

      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-[--text-tertiary] text-sm">坐标系总数</span>
          <span className="badge-running">{transforms.length}</span>
        </div>
        {transforms.length === 0 ? (
          <div className="text-sm text-[--text-tertiary] py-8 text-center">
            暂无 TF 数据,点击刷新获取
          </div>
        ) : (
          <AnimatePresence>
            {roots.length > 0 ? (
              roots.map((root) => (
                <div key={root} className="space-y-1">
                  <TFTreeNode name={root} childrenMap={childrenMap} depth={0} />
                </div>
              ))
            ) : (
              <div className="text-sm text-[--text-tertiary] py-8 text-center">
                未找到根坐标系,可能存在环路
              </div>
            )}
          </AnimatePresence>
        )}
      </GlassCard>
    </div>
  );
}
