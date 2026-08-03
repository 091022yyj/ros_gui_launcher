import { GlassCard } from "./GlassCard";
import { SpringButton } from "./SpringButton";

/** 场景管理页 */
export function SceneManager() {
  const scenes = ["建图 (gmapping)", "导航 (move_base)", "巡检"];

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">场景管理</h2>
      <div className="grid grid-cols-3 gap-4">
        {scenes.map((scene, i) => (
          <GlassCard key={scene} className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">🎬</span>
              <span className="font-semibold">{scene}</span>
            </div>
            <p className="text-xs text-[--text-tertiary] mb-4">
              一键启动该场景下的所有任务
            </p>
            <SpringButton variant={i === 0 ? "primary" : "secondary"} className="w-full">
              应用场景
            </SpringButton>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}
