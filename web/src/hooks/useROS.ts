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
};
