export type AIConfig = {
  mode: "demo" | "byok";
  base_url: string;
  api_key: string;
  text_model: string;
  image_model: string;
  tts_model: string;
  tts_voice: string;
};

export const DEFAULT_AI: AIConfig = {
  mode: "demo",
  base_url: "https://api.openai.com/v1",
  api_key: "",
  text_model: "gpt-4o-mini",
  image_model: "gpt-image-1",
  tts_model: "gpt-4o-mini-tts",
  tts_voice: "alloy",
};

export const GENRES = [
  "都市逆袭",
  "古装权谋",
  "甜宠恋爱",
  "悬疑复仇",
  "校园青春",
  "玄幻战神",
];

export const STYLES = ["真人写实", "日系动画", "国风水墨", "赛博霓虹", "复古胶片"];
export const RATIOS = ["9:16", "16:9", "1:1", "4:3"];

export const GENRE_COLORS: Record<string, string> = {
  都市逆袭: "#ff6b4a",
  古装权谋: "#c9a227",
  甜宠恋爱: "#ff8fa3",
  悬疑复仇: "#5aa9e6",
  校园青春: "#7bc96f",
  玄幻战神: "#9b7bff",
};

export type Project = {
  id: string;
  title: string;
  genre: string;
  style: string;
  ratio: string;
  episode_count: number;
  duration: number;
  logline: string;
  synopsis: string;
  created_at: string;
  updated_at: string;
  cover_url?: string;
  stats?: { episodes: number; shots: number; characters: number };
};

export type Character = {
  id: string;
  project_id: string;
  name: string;
  role: string;
  gender: string;
  age: string;
  appearance: string;
  personality: string;
  arc: string;
  prompt: string;
  image_asset: string;
  image_url: string;
};

export type Shot = {
  id: string;
  episode_id: string;
  idx: number;
  shot_type: string;
  camera: string;
  duration: number;
  location: string;
  description: string;
  dialogue: string;
  prompt: string;
  image_asset: string;
  video_asset: string;
  audio_asset: string;
  image_url: string;
  video_url: string;
  audio_url: string;
};

export type Episode = {
  id: string;
  project_id: string;
  idx: number;
  title: string;
  summary: string;
  script: string;
  status: string;
  shots: Shot[];
  shot_count: number;
};

export type Asset = {
  id: string;
  project_id: string;
  kind: string;
  name: string;
  mime: string;
  source: string;
  url: string;
  created_at: string;
};

export type ProjectDetail = {
  project: Project;
  characters: Character[];
  episodes: Episode[];
  assets: Asset[];
  stats: {
    episodes: number;
    shots: number;
    characters: number;
    assets: number;
    scripts: number;
  };
};

export type GenerationResult = {
  source: "ai" | "demo";
  warning?: string | null;
};
