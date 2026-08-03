/** Python后端API客户端 */

const API = "http://localhost:8000";

export interface Task {
  path: string;
  args: string;
  auto_restart: boolean;
  auto_start: boolean;
}

export interface Config {
  ros_setup: string;
  ws_setup: string;
  start_delay: number;
  launch_files: Task[];
  py_files: Task[];
  [key: string]: unknown;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return res.json();
}

/** 等待后端就绪(Tauri已自动启动后端,等待其启动完成) */
export async function waitForBackend(maxWaitMs = 10000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const res = await fetch(`${API}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return true;
    } catch {
      // 后端还没就绪,继续等待
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/api/health"),

  systemInfo: () =>
    request<{ cpu: number; memory: number; disk: number; hostname: string }>(
      "/api/system/info"
    ),

  getConfig: () => request<{ config: Config }>("/api/config"),

  saveConfig: (config: Partial<Config>) =>
    request<{ success: boolean; error?: string }>("/api/config", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  getTasks: () =>
    request<{ tasks: { launch: Task[]; py: Task[] } }>("/api/tasks"),

  startTask: (kind: "launch" | "py", task: Task) =>
    request<{ success: boolean; error?: string; command?: string }>(
      `/api/tasks/${kind}/start`,
      { method: "POST", body: JSON.stringify(task) }
    ),

  stopTask: (task: Task) =>
    request<{ success: boolean; error?: string }>("/api/tasks/stop", {
      method: "POST",
      body: JSON.stringify(task),
    }),

  rosNodes: () =>
    request<{ nodes: string[]; error?: string }>("/api/ros/nodes"),

  rosTopics: () =>
    request<{ topics: string[]; error?: string }>("/api/ros/topics"),

  rosExec: (cmd: string, timeout = 8) =>
    request<{ success: boolean; output: string; error?: string; code: number }>(
      "/api/ros/exec",
      { method: "POST", body: JSON.stringify({ cmd, timeout }) }
    ),

  rosBattery: () =>
    request<{ battery: string; error?: string }>("/api/ros/battery"),

  rosTF: () =>
    request<{ transforms: { parent: string; child: string }[]; error?: string }>(
      "/api/ros/tf"
    ),

  gazeboStatus: () =>
    request<{ running: boolean }>("/api/gazebo/status"),

  gazeboControl: (action: string, data: Record<string, unknown> = {}) =>
    request<{ success: boolean; output?: string; error?: string }>(
      "/api/gazebo/control",
      { method: "POST", body: JSON.stringify({ action, ...data }) }
    ),
};
