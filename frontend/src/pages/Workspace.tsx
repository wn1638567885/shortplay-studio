import { useEffect, useMemo, useState } from "react";
import { apiClient, copyText, exportUrl, speak } from "../api";
import { Markdown } from "../components/Markdown";
import { GENRE_COLORS, type Asset, type Character, type Episode, type ProjectDetail, type Shot } from "../types";
import { Empty, Field, Spinner, useApp } from "../ui";

type Tab = "overview" | "script" | "storyboard" | "characters" | "assets" | "export";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "总览与分集" },
  { key: "script", label: "剧本" },
  { key: "storyboard", label: "分镜" },
  { key: "characters", label: "角色" },
  { key: "assets", label: "素材" },
  { key: "export", label: "导出" },
];

export function Workspace({ pid, onBack, aiMode }: { pid: string; onBack: () => void; aiMode: "demo" | "byok" }) {
  const { notify, openSettings } = useApp();
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
  const [epId, setEpId] = useState("");
  const [busy, setBusy] = useState("");

  const reload = async () => {
    const data = await apiClient.getProject(pid);
    setDetail(data);
    setEpId((prev) => (data.episodes.some((e) => e.id === prev) ? prev : data.episodes[0]?.id || ""));
    return data;
  };

  useEffect(() => {
    let alive = true;
    setLoading(true);
    apiClient
      .getProject(pid)
      .then((data) => {
        if (!alive) return;
        setDetail(data);
        setEpId((prev) => (data.episodes.some((e) => e.id === prev) ? prev : data.episodes[0]?.id || ""));
      })
      .catch((err) => notify(err?.message || "加载项目失败", "err"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [pid]);

  const run = async (key: string, fn: () => Promise<any>, success?: string) => {
    setBusy(key);
    try {
      const res = await fn();
      await reload();
      if (res?.warning) notify(res.warning, "err");
      else if (success) notify(success, "ok");
      return res;
    } catch (err: any) {
      notify(err?.message || "操作失败", "err");
    } finally {
      setBusy("");
    }
  };

  const episode = useMemo(
    () => detail?.episodes.find((e) => e.id === epId) || detail?.episodes[0] || null,
    [detail, epId],
  );

  if (loading) {
    return (
      <div className="page">
        <div className="loading-row">
          <Spinner /> 正在打开项目…
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="page">
        <Empty icon="⚠" title="项目打不开" desc="可能已被删除，返回列表重新创建。" action={<button className="btn" onClick={onBack}>返回列表</button>} />
      </div>
    );
  }

  const { project, stats } = detail;
  const color = GENRE_COLORS[project.genre] || "#ff6b4a";
  const demoMode = aiMode === "demo";
  const scripted = detail.episodes.filter((e) => e.script).length;
  const shotEpisodes = detail.episodes.filter((e) => e.shots.length).length;

  return (
    <div className="page workspace">
      <button className="back-link" onClick={onBack}>
        ← 项目列表
      </button>

      <header className="ws-head">
        <div className="ws-title">
          <span className="genre-pill" style={{ borderColor: `${color}55`, color }}>
            {project.genre}
          </span>
          <h1>{project.title}</h1>
          <div className="meta-row">
            <span>{project.episode_count} 集</span>
            <span className="dot">·</span>
            <span>{project.duration}s / 集</span>
            <span className="dot">·</span>
            <span>{project.ratio}</span>
            <span className="dot">·</span>
            <span>{project.style}</span>
          </div>
        </div>
        <div className="ws-side">
          <div className="progress-box">
            <div>
              <b>{scripted}</b>
              <span>集有剧本</span>
            </div>
            <div>
              <b>{shotEpisodes}</b>
              <span>集有分镜</span>
            </div>
            <div>
              <b>{stats.shots}</b>
              <span>个镜头</span>
            </div>
          </div>
          <button className="btn ghost sm" onClick={openSettings}>
            {demoMode ? "演示模式 · 接入自己的密钥" : "AI 设置"}
          </button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? "active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <OverviewTab detail={detail} busy={busy} run={run} reload={reload} notify={notify} setTab={setTab} setEpId={setEpId} />
      )}
      {tab === "script" && (
        <ScriptTab detail={detail} episode={episode} epId={epId} setEpId={setEpId} busy={busy} run={run} reload={reload} notify={notify} />
      )}
      {tab === "storyboard" && (
        <StoryboardTab detail={detail} episode={episode} epId={epId} setEpId={setEpId} busy={busy} run={run} reload={reload} notify={notify} demoMode={demoMode} />
      )}
      {tab === "characters" && (
        <CharactersTab detail={detail} busy={busy} run={run} reload={reload} notify={notify} />
      )}
      {tab === "assets" && <AssetsTab detail={detail} reload={reload} notify={notify} />}
      {tab === "export" && <ExportTab detail={detail} />}
    </div>
  );
}

function EpisodeChips({
  episodes,
  active,
  onPick,
  color,
}: {
  episodes: Episode[];
  active: string;
  onPick: (id: string) => void;
  color: string;
}) {
  return (
    <div className="ep-chips">
      {episodes.map((ep) => (
        <button
          key={ep.id}
          className={`ep-chip ${active === ep.id ? "active" : ""}`}
          onClick={() => onPick(ep.id)}
        >
          <span className="ep-chip-no" style={active === ep.id ? { background: color } : undefined}>
            {ep.idx}
          </span>
          <span className="ep-chip-title">{ep.title}</span>
          {ep.shots.length > 0 && <i className="ep-chip-dot" />}
        </button>
      ))}
    </div>
  );
}

function OverviewTab({
  detail,
  busy,
  run,
  reload,
  notify,
  setTab,
  setEpId,
}: {
  detail: ProjectDetail;
  busy: string;
  run: (key: string, fn: () => Promise<any>, success?: string) => Promise<any>;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
  setTab: (t: Tab) => void;
  setEpId: (id: string) => void;
}) {
  const { project } = detail;
  const [logline, setLogline] = useState(project.logline);
  const [synopsis, setSynopsis] = useState(project.synopsis);

  useEffect(() => {
    setLogline(project.logline);
    setSynopsis(project.synopsis);
  }, [project.logline, project.synopsis]);

  const saveStory = () =>
    run(
      "save-story",
      () => apiClient.updateProject(project.id, { logline, synopsis }),
      "故事线已保存",
    );

  const batchStoryboard = async () => {
    if (!window.confirm("将为所有还没分镜的集数生成分镜，可能耗时较长，继续？")) return;
    await run(
      "batch",
      async () => {
        for (const ep of detail.episodes) {
          if (ep.shots.length === 0) {
            await apiClient.generateStoryboard(ep.id);
          }
        }
        return null;
      },
      "全部集数分镜已生成",
    );
  };

  return (
    <div className="overview">
      <div className="overview-grid">
        <div className="card">
          <div className="card-head">
            <h3>故事线</h3>
            <span className="muted small">可以直接手改，也可以一键让 AI 重写</span>
          </div>
          <Field label="一句话故事线">
            <textarea
              rows={2}
              value={logline}
              onChange={(e) => setLogline(e.target.value)}
              placeholder="被踩进泥里的人，如何一步步翻盘…"
            />
          </Field>
          <Field label="故事简介">
            <textarea
              rows={5}
              value={synopsis}
              onChange={(e) => setSynopsis(e.target.value)}
              placeholder="用 150 字讲清楚人物、处境、钩子。"
            />
          </Field>
          <div className="row-actions">
            <button className="btn primary" onClick={saveStory} disabled={!!busy}>
              {busy === "save-story" && <Spinner />}保存
            </button>
            <button
              className="btn ghost"
              onClick={() =>
                run("outline", () => apiClient.generateOutline(project.id), "整部大纲已生成")
              }
              disabled={!!busy}
            >
              {busy === "outline" && <Spinner />}生成整体大纲
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>项目设定</h3>
          </div>
          <dl className="meta-list">
            <div>
              <dt>题材</dt>
              <dd>{project.genre}</dd>
            </div>
            <div>
              <dt>风格</dt>
              <dd>{project.style}</dd>
            </div>
            <div>
              <dt>画幅</dt>
              <dd>{project.ratio}</dd>
            </div>
            <div>
              <dt>集数 / 时长</dt>
              <dd>
                {project.episode_count} 集 · {project.duration}s
              </dd>
            </div>
          </dl>
          <div className="stack-actions">
            <button
              className="btn ghost"
              onClick={() =>
                run("outline", () => apiClient.generateOutline(project.id), "整部大纲已生成")
              }
              disabled={!!busy}
            >
              {busy === "outline" ? <Spinner /> : "🪄"} 生成 / 重写大纲
            </button>
            <button
              className="btn ghost"
              onClick={() =>
                run("chars", () => apiClient.generateCharacters(project.id), "角色设定已生成")
              }
              disabled={!!busy}
            >
              {busy === "chars" ? <Spinner /> : "👥"} 重新生成角色
            </button>
            <button className="btn ghost" onClick={batchStoryboard} disabled={!!busy}>
              {busy === "batch" ? <Spinner /> : "🎬"} 全部集数一键分镜
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>分集列表</h3>
          <span className="muted small">每集都可以单独生成剧本和分镜</span>
        </div>
        {detail.episodes.length === 0 ? (
          <Empty
            icon="🧩"
            title="还没有分集"
            desc="先生成整体大纲，系统会按集数拆出分集卡。"
            action={
              <button
                className="btn primary"
                onClick={() =>
                  run("outline", () => apiClient.generateOutline(project.id), "整部大纲已生成")
                }
              >
                生成整体大纲
              </button>
            }
          />
        ) : (
          <div className="ep-table">
            {detail.episodes.map((ep) => (
              <div className="ep-row" key={ep.id}>
                <span className="ep-no">{String(ep.idx).padStart(2, "0")}</span>
                <div className="ep-info">
                  <strong>{ep.title}</strong>
                  <p>{ep.summary}</p>
                </div>
                <span className={`status ${ep.shots.length ? "done" : ep.script ? "mid" : ""}`}>
                  {ep.shots.length ? "已分镜" : ep.script ? "有剧本" : "待生成"}
                </span>
                <div className="ep-actions">
                  <button
                    className="btn sm ghost"
                    disabled={!!busy}
                    onClick={() => run(`script-${ep.id}`, () => apiClient.generateScript(ep.id), "剧本已生成")}
                  >
                    {busy === `script-${ep.id}` ? <Spinner /> : null}写剧本
                  </button>
                  <button
                    className="btn sm ghost"
                    disabled={!!busy}
                    onClick={() => run(`board-${ep.id}`, () => apiClient.generateStoryboard(ep.id), "分镜已生成")}
                  >
                    {busy === `board-${ep.id}` ? <Spinner /> : null}拆分镜
                  </button>
                  <button
                    className="btn sm"
                    onClick={() => {
                      setEpId(ep.id);
                      setTab(ep.script ? "script" : "storyboard");
                    }}
                  >
                    打开
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ScriptTab({
  detail,
  episode,
  epId,
  setEpId,
  busy,
  run,
  reload,
  notify,
}: {
  detail: ProjectDetail;
  episode: Episode | null;
  epId: string;
  setEpId: (id: string) => void;
  busy: string;
  run: (key: string, fn: () => Promise<any>, success?: string) => Promise<any>;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const color = GENRE_COLORS[detail.project.genre] || "#ff6b4a";

  useEffect(() => {
    setEditing(false);
    setDraft(episode?.script || "");
  }, [episode?.id, episode?.script]);

  if (!episode) {
    return <Empty icon="📄" title="还没有分集" desc="先回到总览生成整体大纲。" />;
  }

  const generate = () =>
    run("script", () => apiClient.generateScript(episode.id), "剧本已生成");

  const save = async () => {
    await run(
      "save-script",
      () => apiClient.updateEpisode(episode.id, { script: draft, status: "已生成剧本" }),
      "剧本已保存",
    );
    setEditing(false);
  };

  return (
    <div className="script-tab">
      <EpisodeChips episodes={detail.episodes} active={epId} onPick={setEpId} color={color} />
      <div className="card">
        <div className="card-head">
          <div>
            <h3>
              第 {episode.idx} 集 · {episode.title}
            </h3>
            <p className="muted small">{episode.summary}</p>
          </div>
          <div className="row-actions">
            <button className="btn ghost sm" onClick={generate} disabled={!!busy}>
              {busy === "script" && <Spinner />}
              {episode.script ? "重新生成" : "生成本集剧本"}
            </button>
            {episode.script && !editing && (
              <button
                className="btn sm"
                onClick={() => {
                  setDraft(episode.script);
                  setEditing(true);
                }}
              >
                编辑
              </button>
            )}
            {editing && (
              <>
                <button className="btn sm ghost" onClick={() => setEditing(false)}>
                  取消
                </button>
                <button className="btn sm primary" onClick={save} disabled={!!busy}>
                  {busy === "save-script" && <Spinner />}保存
                </button>
              </>
            )}
          </div>
        </div>

        {editing ? (
          <textarea
            className="script-editor"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={24}
            spellCheck={false}
          />
        ) : episode.script ? (
          <Markdown
            text={episode.script
              .replace(/^\s*#\s+[^\n]*\n+/, "")
              .replace(/^\s*>\s*本集摘要：[^\n]*\n+/, "")}
          />
        ) : (
          <Empty
            icon="✍️"
            title="这一集还没有剧本"
            desc="演示模式会用内置题材模板生成一份可直接改的场次剧本。"
            action={
              <button className="btn primary" onClick={generate} disabled={!!busy}>
                {busy === "script" && <Spinner />}生成本集剧本
              </button>
            }
          />
        )}
      </div>
    </div>
  );
}

function StoryboardTab({
  detail,
  episode,
  epId,
  setEpId,
  busy,
  run,
  reload,
  notify,
  demoMode,
}: {
  detail: ProjectDetail;
  episode: Episode | null;
  epId: string;
  setEpId: (id: string) => void;
  busy: string;
  run: (key: string, fn: () => Promise<any>, success?: string) => Promise<any>;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
  demoMode: boolean;
}) {
  const { openSettings } = useApp();
  const color = GENRE_COLORS[detail.project.genre] || "#ff6b4a";

  if (!episode) {
    return <Empty icon="🎬" title="还没有分集" desc="先回到总览生成整体大纲。" />;
  }

  const generate = () =>
    run("board", () => apiClient.generateStoryboard(episode.id), "分镜已生成");

  const batchVideo = async () => {
    if (demoMode) {
      notify("演示模式不调用云端视频，请先在 AI 设置中接入文生视频模型", "err");
      openSettings();
      return;
    }
    if (!episode.shots.length) {
      notify("这一集还没有分镜", "err");
      return;
    }
    if (!window.confirm("将为该集还没有视频的镜头依次提交生成任务，继续？")) return;
    const res = await run("batch-video", () => apiClient.generateEpisodeVideos(episode.id));
    if (!res) return;
    if (res.errors?.length) {
      notify(`已提交 ${res.submitted} 个，${res.errors.length} 个失败：${res.errors[0].message}`, "err");
    } else if (res.submitted) {
      notify(`已提交 ${res.submitted} 个镜头视频任务，正在生成…`, "ok");
    } else {
      notify("该集所有镜头都已有视频或正在生成", "ok");
    }
  };

  const combineFinal = async () => {
    if (!episode.shots.every((s) => s.video_asset)) {
      notify("还有镜头没有视频，请先生成或上传全部镜头视频", "err");
      return;
    }
    if (!window.confirm("将把该集全部镜头视频按顺序拼接为一个成片，继续？")) return;
    await run("final-video", () => apiClient.generateEpisodeFinal(episode.id), "整集成片已合成");
  };

  return (
    <div className="storyboard-tab">
      <EpisodeChips episodes={detail.episodes} active={epId} onPick={setEpId} color={color} />
      <div className="card-head board-head">
        <div>
          <h3>
            第 {episode.idx} 集分镜 · {episode.shots.length} 个镜头
          </h3>
          <p className="muted small">景别、运镜、台词和绘图提示词都可以逐镜修改。</p>
        </div>
        <div className="row-actions">
          <button className="btn ghost sm" onClick={batchVideo} disabled={!!busy || !episode.shots.length}>
            {busy === "batch-video" ? <Spinner /> : "🎥"} 整集生成视频
          </button>
          <button
            className="btn ghost sm"
            onClick={combineFinal}
            disabled={!!busy || !episode.shots.length}
          >
            {busy === "final-video" ? <Spinner /> : "🎬"} 合成整集成片
          </button>
          <button className="btn primary sm" onClick={generate} disabled={!!busy}>
            {busy === "board" && <Spinner />}
            {episode.shots.length ? "重新拆分镜" : "生成这一集分镜"}
          </button>
        </div>
      </div>

      {demoMode && (
        <div className="banner">
          当前是演示模式：生成的画面是带提示词的分镜示意图，零调用成本。接入图像 / 视频模型后会生成真实画面与镜头视频。
          <button className="link-btn" onClick={openSettings}>
            去设置
          </button>
        </div>
      )}

      {episode.final_video_url && (
        <div className="card final-video">
          <div className="card-head">
            <h3>第 {episode.idx} 集成片</h3>
            <a className="link-btn" href={episode.final_video_url} download={`第${episode.idx}集成片.mp4`}>
              下载成片
            </a>
          </div>
          <video src={episode.final_video_url} controls playsInline />
        </div>
      )}

      {episode.shots.length === 0 ? (
        <Empty
          icon="🎞"
          title="这一集还没有分镜"
          desc="按 60–90 秒一集拆成 10 个左右的镜头，并自动写好绘图提示词。"
          action={
            <button className="btn primary" onClick={generate} disabled={!!busy}>
              {busy === "board" && <Spinner />}生成本集分镜
            </button>
          }
        />
      ) : (
        <div className="shot-grid">
          {episode.shots.map((shot) => (
            <ShotCard
              key={shot.id}
              shot={shot}
              ratio={detail.project.ratio}
              busy={busy}
              run={run}
              reload={reload}
              notify={notify}
              demoMode={demoMode}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ShotCard({
  shot,
  ratio,
  busy,
  run,
  reload,
  notify,
  demoMode,
}: {
  shot: Shot;
  ratio: string;
  busy: string;
  run: (key: string, fn: () => Promise<any>, success?: string) => Promise<any>;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
  demoMode: boolean;
}) {
  const { openSettings } = useApp();
  const [editing, setEditing] = useState(false);
  const [video, setVideo] = useState({ status: shot.video_status || "", progress: 0 });
  const [draft, setDraft] = useState({
    shot_type: shot.shot_type,
    camera: shot.camera,
    duration: shot.duration,
    description: shot.description,
    dialogue: shot.dialogue,
    prompt: shot.prompt,
  });

  useEffect(() => {
    setDraft({
      shot_type: shot.shot_type,
      camera: shot.camera,
      duration: shot.duration,
      description: shot.description,
      dialogue: shot.dialogue,
      prompt: shot.prompt,
    });
  }, [shot.id, shot.shot_type, shot.camera, shot.duration, shot.description, shot.dialogue, shot.prompt]);

  const genImage = () =>
    run(`img-${shot.id}`, () => apiClient.generateShotImage(shot.id), "画面已生成");

  const videoStatus = video.status || shot.video_status;
  const videoActive = ["queued", "in_progress", "processing"].includes(videoStatus);

  useEffect(() => {
    if (shot.video_status) setVideo({ status: shot.video_status, progress: 0 });
  }, [shot.id, shot.video_status]);

  useEffect(() => {
    if (!videoActive) return;
    let stopped = false;
    const tick = async () => {
      try {
        const res = await apiClient.getShotVideoStatus(shot.id);
        if (stopped) return;
        setVideo({ status: res.status, progress: res.progress || 0 });
        if (res.status === "completed") {
          notify("镜头视频已生成", "ok");
          await reload();
        } else if (res.status === "failed") {
          notify(res.message || "视频生成失败", "err");
        }
      } catch (err: any) {
        if (!stopped) notify(err?.message || "查询视频状态失败", "err");
      }
    };
    tick();
    const timer = window.setInterval(tick, 5000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [videoActive, shot.id]);

  const genVideo = async () => {
    if (demoMode) {
      notify("演示模式不调用云端视频，请先在 AI 设置中接入文生视频模型", "err");
      openSettings();
      return;
    }
    const res = await run(`vid-${shot.id}`, () => apiClient.generateShotVideo(shot.id));
    if (res?.status === "completed") {
      notify("视频已生成", "ok");
    } else if (res?.job_id) {
      setVideo({ status: res.status || "queued", progress: res.progress || 0 });
      notify("视频任务已提交，正在生成…", "ok");
    }
  };

  const save = async () => {
    await run(
      `save-shot-${shot.id}`,
      () => apiClient.updateShot(shot.id, draft),
      "镜头已保存",
    );
    setEditing(false);
  };

  const upload = (file: File | undefined) => {
    if (!file) return;
    const kind = file.type.startsWith("video")
      ? "video"
      : file.type.startsWith("audio")
        ? "audio"
        : "image";
    run(`up-${shot.id}`, () => apiClient.uploadShot(shot.id, file, kind), "素材已上传");
  };

  return (
    <article className="shot-card">
      <div className="shot-thumb" style={{ aspectRatio: ratio.replace(":", " / ") }}>
        {shot.image_url ? (
          <img src={shot.image_url} alt={`镜头 ${shot.idx}`} />
        ) : (
          <div className="shot-placeholder">
            <span className="shot-index">{String(shot.idx).padStart(2, "0")}</span>
            <span>未生成画面</span>
          </div>
        )}
        <span className="shot-badge">#{shot.idx}</span>
        <span className="shot-dur">{Number(shot.duration)}s</span>
      </div>

      <div className="shot-body">
        <div className="shot-meta">
          <span className="chip">{shot.shot_type}</span>
          <span className="chip">{shot.camera}</span>
          <span className="muted small">{shot.location}</span>
        </div>

        {editing ? (
          <div className="shot-edit">
            <div className="grid two tight">
              <Field label="景别">
                <input value={draft.shot_type} onChange={(e) => setDraft({ ...draft, shot_type: e.target.value })} />
              </Field>
              <Field label="运镜">
                <input value={draft.camera} onChange={(e) => setDraft({ ...draft, camera: e.target.value })} />
              </Field>
              <Field label="时长（秒）">
                <input
                  type="number"
                  step={0.5}
                  value={draft.duration}
                  onChange={(e) => setDraft({ ...draft, duration: Number(e.target.value) })}
                />
              </Field>
            </div>
            <Field label="画面描述">
              <textarea rows={3} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
            </Field>
            <Field label="台词">
              <textarea rows={2} value={draft.dialogue} onChange={(e) => setDraft({ ...draft, dialogue: e.target.value })} />
            </Field>
            <Field label="绘图提示词">
              <textarea rows={3} value={draft.prompt} onChange={(e) => setDraft({ ...draft, prompt: e.target.value })} />
            </Field>
            <div className="row-actions">
              <button className="btn sm primary" onClick={save} disabled={!!busy}>
                {busy === `save-shot-${shot.id}` && <Spinner />}保存
              </button>
              <button className="btn sm ghost" onClick={() => setEditing(false)}>
                取消
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="shot-desc">{shot.description}</p>
            {shot.dialogue && <blockquote className="shot-line">“{shot.dialogue}”</blockquote>}
            <p className="prompt-text" title={shot.prompt}>
              {shot.prompt}
            </p>
          </>
        )}

        {shot.video_url && <video className="shot-video" src={shot.video_url} controls />}
        {shot.audio_url && <audio className="shot-audio" src={shot.audio_url} controls />}

        {!shot.video_url && videoStatus && videoStatus !== "completed" && (
          <div className={`video-status ${videoStatus === "failed" ? "failed" : ""}`}>
            {videoStatus === "failed"
              ? "视频生成失败，可重新尝试"
              : `视频生成中${video.progress ? ` · ${video.progress}%` : "…"}`}
          </div>
        )}

        <div className="shot-actions">
          <button className="btn sm ghost" onClick={genImage} disabled={!!busy}>
            {busy === `img-${shot.id}` ? <Spinner /> : "🖼"} 生成画面
          </button>
          <button className="btn sm ghost" onClick={genVideo} disabled={!!busy || videoActive}>
            {busy === `vid-${shot.id}` ? <Spinner /> : "🎥"} {shot.video_url ? "重生成视频" : "生成视频"}
          </button>
          <label className="btn sm ghost file-btn">
            上传素材
            <input type="file" accept="video/*,image/*,audio/*" onChange={(e) => upload(e.target.files?.[0])} />
          </label>
          {shot.dialogue && (
            <button className="btn sm ghost" onClick={() => (speak(shot.dialogue) ? null : notify("浏览器不支持朗读", "err"))}>
              🔊 试听
            </button>
          )}
          <button
            className="btn sm ghost"
            onClick={async () => {
              const ok = await copyText(shot.prompt);
              notify(ok ? "提示词已复制" : "复制失败", ok ? "ok" : "err");
            }}
          >
            复制提示词
          </button>
          <button className="btn sm ghost" onClick={() => setEditing((v) => !v)}>
            {editing ? "收起" : "编辑"}
          </button>
        </div>
      </div>
    </article>
  );
}

function CharactersTab({
  detail,
  busy,
  run,
  reload,
  notify,
}: {
  detail: ProjectDetail;
  busy: string;
  run: (key: string, fn: () => Promise<any>, success?: string) => Promise<any>;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
}) {
  return (
    <div className="characters-tab">
      <div className="card-head board-head">
        <div>
          <h3>角色设定</h3>
          <p className="muted small">形象提示词用于保持跨镜头的角色一致性。</p>
        </div>
        <button
          className="btn primary sm"
          disabled={!!busy}
          onClick={() => run("chars", () => apiClient.generateCharacters(detail.project.id), "角色设定已生成")}
        >
          {busy === "chars" && <Spinner />}
          生成 / 重写角色
        </button>
      </div>

      {detail.characters.length === 0 ? (
        <Empty
          icon="👥"
          title="还没有角色"
          desc="生成大纲时会自动带出角色，也可以在这里单独重写。"
          action={
            <button
              className="btn primary"
              disabled={!!busy}
              onClick={() => run("chars", () => apiClient.generateCharacters(detail.project.id), "角色设定已生成")}
            >
              生成角色
            </button>
          }
        />
      ) : (
        <div className="char-grid">
          {detail.characters.map((c) => (
            <CharacterCard
              key={c.id}
              character={c}
              busy={busy}
              run={run}
              reload={reload}
              notify={notify}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CharacterCard({
  character,
  busy,
  run,
  reload,
  notify,
}: {
  character: Character;
  busy: string;
  run: (key: string, fn: () => Promise<any>, success?: string) => Promise<any>;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
}) {
  const [editing, setEditing] = useState(false);
  const [prompt, setPrompt] = useState(character.prompt);

  useEffect(() => setPrompt(character.prompt), [character.prompt]);

  const save = async () => {
    await run(`save-char-${character.id}`, () => apiClient.updateCharacter(character.id, { prompt }), "提示词已保存");
    setEditing(false);
  };

  return (
    <article className="char-card">
      <div className="char-portrait">
        {character.image_url ? (
          <img src={character.image_url} alt={character.name} />
        ) : (
          <div className="char-placeholder">{character.name.slice(0, 1)}</div>
        )}
      </div>
      <div className="char-body">
        <div className="char-title">
          <h4>{character.name}</h4>
          <span className="muted small">{character.role}</span>
        </div>
        <div className="char-facts">
          <span>{character.gender}</span>
          <span>{character.age} 岁</span>
        </div>
        <p className="char-desc">
          <b>外貌</b>
          {character.appearance}
        </p>
        <p className="char-desc">
          <b>性格</b>
          {character.personality}
        </p>
        <p className="char-desc">
          <b>弧光</b>
          {character.arc}
        </p>

        {editing ? (
          <div className="shot-edit">
            <Field label="形象提示词">
              <textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
            </Field>
            <div className="row-actions">
              <button className="btn sm primary" onClick={save} disabled={!!busy}>
                保存
              </button>
              <button className="btn sm ghost" onClick={() => setEditing(false)}>
                取消
              </button>
            </div>
          </div>
        ) : (
          <p className="prompt-text">{character.prompt}</p>
        )}

        <div className="shot-actions">
          <button
            className="btn sm ghost"
            disabled={!!busy}
            onClick={() => run(`cimg-${character.id}`, () => apiClient.generateCharacterImage(character.id), "角色形象已生成")}
          >
            {busy === `cimg-${character.id}` ? <Spinner /> : "🎨"} 生成形象
          </button>
          <button className="btn sm ghost" onClick={() => setEditing((v) => !v)}>
            {editing ? "收起" : "改提示词"}
          </button>
          <button
            className="btn sm ghost"
            onClick={async () => {
              const ok = await copyText(character.prompt);
              notify(ok ? "提示词已复制" : "复制失败", ok ? "ok" : "err");
            }}
          >
            复制
          </button>
        </div>
      </div>
    </article>
  );
}

function AssetsTab({
  detail,
  reload,
  notify,
}: {
  detail: ProjectDetail;
  reload: () => Promise<ProjectDetail>;
  notify: (msg: string, kind?: "ok" | "err") => void;
}) {
  const [kind, setKind] = useState("image");
  const [uploading, setUploading] = useState(false);

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    try {
      await apiClient.uploadAsset(detail.project.id, file, kind);
      await reload();
      notify("素材已上传", "ok");
    } catch (err: any) {
      notify(err?.message || "上传失败", "err");
    } finally {
      setUploading(false);
    }
  };

  const remove = async (asset: Asset) => {
    if (!window.confirm("删除这个素材？引用它的镜头会解除关联。")) return;
    try {
      await apiClient.deleteAsset(asset.id);
      await reload();
      notify("已删除", "ok");
    } catch (err: any) {
      notify(err?.message || "删除失败", "err");
    }
  };

  return (
    <div className="assets-tab">
      <div className="card upload-bar">
        <div>
          <h3>素材库</h3>
          <p className="muted small">上传参考图、生成画面、成片或配音，统一放在项目里。</p>
        </div>
        <div className="upload-controls">
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="image">图片</option>
            <option value="video">视频</option>
            <option value="audio">音频</option>
            <option value="other">其他</option>
          </select>
          <label className="btn primary sm file-btn">
            {uploading ? <Spinner /> : "+"} 上传素材
            <input type="file" onChange={(e) => upload(e.target.files?.[0])} />
          </label>
        </div>
      </div>

      {detail.assets.length === 0 ? (
        <Empty icon="🗂" title="素材库是空的" desc="生成的分镜画面和上传的文件都会出现在这里。" />
      ) : (
        <div className="asset-grid">
          {detail.assets.map((asset) => (
            <div className="asset-card" key={asset.id}>
              <div className="asset-preview">
                {asset.mime.startsWith("image/") ? (
                  <img src={asset.url} alt={asset.name} />
                ) : asset.mime.startsWith("video/") ? (
                  <video src={asset.url} controls />
                ) : asset.mime.startsWith("audio/") ? (
                  <audio src={asset.url} controls />
                ) : (
                  <span className="asset-file">FILE</span>
                )}
              </div>
              <div className="asset-meta">
                <span className="asset-name" title={asset.name}>
                  {asset.name}
                </span>
                <span className="muted small">
                  {asset.source === "upload" ? "上传" : asset.source === "ai" ? "AI 生成" : "演示"}
                </span>
              </div>
              <button className="asset-del" onClick={() => remove(asset)}>
                删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ExportTab({ detail }: { detail: ProjectDetail }) {
  const items = [
    {
      key: "md",
      title: "Markdown 制作稿",
      desc: "故事线、角色、全部剧本和分镜表，适合发给编剧或剪辑。",
      icon: "📝",
    },
    {
      key: "csv",
      title: "CSV 分镜表",
      desc: "逐镜头表格：景别、运镜、时长、画面、台词、提示词。",
      icon: "📊",
    },
    {
      key: "json",
      title: "JSON 项目数据",
      desc: "完整结构化数据，方便接入你自己的工具链或做二次开发。",
      icon: "🧩",
    },
  ];
  return (
    <div className="export-tab">
      <div className="export-grid">
        {items.map((item) => (
          <div className="card export-card" key={item.key}>
            <span className="export-icon">{item.icon}</span>
            <h3>{item.title}</h3>
            <p className="muted">{item.desc}</p>
            <a className="btn primary sm" href={exportUrl(detail.project.id, item.key)}>
              下载 .{item.key}
            </a>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>导出说明</h3>
        <p className="muted">
          导出内容来自当前项目的最新数据。演示模式下的分镜画面是 SVG 示意图，提示词可以直接复制到即梦、可灵、
          Midjourney 等工具里继续生成。视频部分目前以“提示词 + 素材上传”的方式接入，不消耗平台额度。
        </p>
      </div>
    </div>
  );
}
