import { DEFAULT_AI, type AIConfig, type Asset, type Character, type Episode, type Project, type ProjectDetail, type Shot } from "./types";

const AI_KEY = "shortplay.ai.v1";

export function getAI(): AIConfig {
  try {
    const raw = localStorage.getItem(AI_KEY);
    if (!raw) return { ...DEFAULT_AI };
    return { ...DEFAULT_AI, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_AI };
  }
}

export function setAI(config: AIConfig) {
  localStorage.setItem(AI_KEY, JSON.stringify(config));
}

function encodeHeader(config: AIConfig): string {
  const bytes = new TextEncoder().encode(JSON.stringify(config));
  let bin = "";
  bytes.forEach((b) => {
    bin += String.fromCharCode(b);
  });
  return btoa(bin);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("X-AI-Config", encodeHeader(getAI()));
  const res = await fetch(path, { ...init, headers });
  const text = await res.text();
  let data: any = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = data && typeof data === "object" ? data.detail : data;
    throw new Error(typeof detail === "string" ? detail : `请求失败（${res.status}）`);
  }
  return data as T;
}

export const apiClient = {
  listProjects: () => api<{ items: Project[] }>("/api/projects"),
  createProject: (body: Partial<Project>) =>
    api<ProjectDetail>("/api/projects", { method: "POST", body: JSON.stringify(body) }),
  getProject: (pid: string) => api<ProjectDetail>(`/api/projects/${pid}`),
  updateProject: (pid: string, body: Record<string, unknown>) =>
    api<ProjectDetail>(`/api/projects/${pid}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteProject: (pid: string) => api<{ ok: boolean }>(`/api/projects/${pid}`, { method: "DELETE" }),
  generateOutline: (pid: string) =>
    api<ProjectDetail & { source: string; warning?: string }>(`/api/projects/${pid}/generate/outline`, { method: "POST" }),
  generateCharacters: (pid: string) =>
    api<ProjectDetail & { source: string; warning?: string }>(`/api/projects/${pid}/generate/characters`, { method: "POST" }),
  generateScript: (eid: string) =>
    api<{ episode: Episode; source: string; warning?: string }>(`/api/episodes/${eid}/generate/script`, { method: "POST" }),
  generateStoryboard: (eid: string) =>
    api<Episode & { source: string; warning?: string }>(`/api/episodes/${eid}/generate/storyboard`, { method: "POST" }),
  updateEpisode: (eid: string, body: Record<string, unknown>) =>
    api<Episode>(`/api/episodes/${eid}`, { method: "PATCH", body: JSON.stringify(body) }),
  updateShot: (sid: string, body: Record<string, unknown>) =>
    api<Shot>(`/api/shots/${sid}`, { method: "PATCH", body: JSON.stringify(body) }),
  generateShotImage: (sid: string) =>
    api<{ asset: Asset; shot: Shot; source: string; warning?: string }>(`/api/shots/${sid}/generate/image`, { method: "POST" }),
  generateCharacterImage: (cid: string) =>
    api<{ asset: Asset; character: Character; source: string; warning?: string }>(`/api/characters/${cid}/generate/image`, { method: "POST" }),
  generateVoice: (sid: string) =>
    api<{ asset: Asset; shot: Shot; source: string }>(`/api/shots/${sid}/generate/voice`, { method: "POST" }),
  generateShotVideo: (sid: string) =>
    api<{ job_id?: string; status: string; progress: number; message?: string; shot: Shot }>(
      `/api/shots/${sid}/generate/video`,
      { method: "POST" },
    ),
  getShotVideoStatus: (sid: string) =>
    api<{ status: string; progress: number; message?: string; asset?: Asset; shot: Shot }>(
      `/api/shots/${sid}/video-status`,
    ),
  updateCharacter: (cid: string, body: Record<string, unknown>) =>
    api<Character>(`/api/characters/${cid}`, { method: "PATCH", body: JSON.stringify(body) }),
  createCharacter: (body: Record<string, unknown>) =>
    api<Character>("/api/characters", { method: "POST", body: JSON.stringify(body) }),
  uploadShot: (sid: string, file: File, kind: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("kind", kind);
    return api<{ asset: Asset; shot: Shot }>(`/api/shots/${sid}/upload`, { method: "POST", body: fd });
  },
  uploadAsset: (pid: string, file: File, kind: string) => {
    const fd = new FormData();
    fd.append("project_id", pid);
    fd.append("kind", kind);
    fd.append("file", file);
    return api<{ asset: Asset }>("/api/assets/upload", { method: "POST", body: fd });
  },
  deleteAsset: (aid: string) => api<{ ok: boolean }>(`/api/assets/${aid}`, { method: "DELETE" }),
  testAI: () => api<{ ok: boolean; mode: string; message: string }>("/api/ai/test", { method: "POST" }),
};

export function exportUrl(pid: string, format: string) {
  return `/api/projects/${pid}/export?format=${format}`;
}

export function speak(text: string): boolean {
  if (!("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const clean = text.replace(/[（(][^）)]*[）)]/g, "").trim();
  if (!clean) return false;
  const utter = new SpeechSynthesisUtterance(clean);
  utter.lang = "zh-CN";
  utter.rate = 1.02;
  utter.pitch = 1;
  window.speechSynthesis.speak(utter);
  return true;
}

export async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
