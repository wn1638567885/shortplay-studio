import { useEffect, useState } from "react";
import { apiClient } from "../api";
import { GENRES, GENRE_COLORS, RATIOS, STYLES, type Project } from "../types";
import { Empty, Field, Modal, Spinner, useApp } from "../ui";

type FormState = {
  title: string;
  genre: string;
  style: string;
  ratio: string;
  episode_count: number;
  duration: number;
};

const DEFAULT_FORM: FormState = {
  title: "",
  genre: "都市逆袭",
  style: "真人写实",
  ratio: "9:16",
  episode_count: 12,
  duration: 90,
};

function formatDate(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

export function Projects({ onOpen }: { onOpen: (id: string) => void }) {
  const { notify } = useApp();
  const [items, setItems] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);

  const load = async () => {
    try {
      const res = await apiClient.listProjects();
      setItems(res.items);
    } catch (err: any) {
      notify(err?.message || "加载项目失败", "err");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!form.title.trim()) {
      notify("先给短剧起个名字", "err");
      return;
    }
    setSaving(true);
    try {
      const detail = await apiClient.createProject(form);
      notify("项目已创建，去生成大纲吧", "ok");
      setOpen(false);
      setForm(DEFAULT_FORM);
      onOpen(detail.project.id);
    } catch (err: any) {
      notify(err?.message || "创建失败", "err");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p: Project) => {
    if (!window.confirm(`删除《${p.title}》？剧本、分镜和素材都会一并删除。`)) return;
    try {
      await apiClient.deleteProject(p.id);
      setItems((prev) => prev.filter((item) => item.id !== p.id));
      notify("已删除", "ok");
    } catch (err: any) {
      notify(err?.message || "删除失败", "err");
    }
  };

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-main">
          <span className="eyebrow">SHORTPLAY STUDIO</span>
          <h1>
            把一个想法，
            <br />
            变成一整季短剧。
          </h1>
          <p className="hero-sub">
            大纲、分集剧本、分镜、角色、配音和素材管理放在同一条流水线里。
            不卖积分——先用零成本演示模式跑通，再填自己的密钥升级画面。
          </p>
          <div className="hero-actions">
            <button className="btn primary lg" onClick={() => setOpen(true)}>
              + 新建短剧项目
            </button>
            <span className="hero-note">无需注册 · 无需积分 · 密钥只存在你本地</span>
          </div>
        </div>
        <div className="hero-panel">
          <div className="pipeline">
            {[
              ["01", "设定", "题材 / 风格 / 集数"],
              ["02", "大纲", "故事线 + 分集钩子"],
              ["03", "剧本", "场次 / 台词 / 冲突"],
              ["04", "分镜", "景别 / 运镜 / 提示词"],
              ["05", "画面与配音", "演示或 BYOK"],
              ["06", "导出", "Markdown / CSV / JSON"],
            ].map(([no, title, desc]) => (
              <div className="pipeline-step" key={no}>
                <span className="step-no">{no}</span>
                <div>
                  <strong>{title}</strong>
                  <span>{desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>我的项目</h2>
          <span className="muted">{items.length} 个</span>
        </div>

        {loading ? (
          <div className="loading-row">
            <Spinner /> 正在加载项目…
          </div>
        ) : items.length === 0 ? (
          <Empty
            icon="🎬"
            title="还没有项目"
            desc="新建一个项目，先选题材和集数，剩下的交给半自动流程。"
            action={
              <button className="btn primary" onClick={() => setOpen(true)}>
                新建第一个项目
              </button>
            }
          />
        ) : (
          <div className="project-grid">
            {items.map((p) => {
              const color = GENRE_COLORS[p.genre] || "#ff6b4a";
              return (
                <article className="project-card" key={p.id} onClick={() => onOpen(p.id)}>
                  <div
                    className="project-cover"
                    style={{
                      background: `radial-gradient(120% 90% at 20% 0%, ${color}55 0%, #12121a 62%), #101017`,
                    }}
                  >
                    {p.cover_url ? (
                      <img src={p.cover_url} alt={p.title} />
                    ) : (
                      <span className="cover-glyph">{p.genre.slice(0, 2)}</span>
                    )}
                    <span className="badge">{p.genre}</span>
                    <button
                      className="card-del"
                      onClick={(e) => {
                        e.stopPropagation();
                        remove(p);
                      }}
                    >
                      删除
                    </button>
                  </div>
                  <div className="project-body">
                    <div className="project-title-row">
                      <h3>{p.title}</h3>
                      <span className="muted small">{formatDate(p.updated_at)}</span>
                    </div>
                    <p className="logline">{p.logline || "还没有故事线，进入工作台一键生成。"}</p>
                    <div className="meta-row">
                      <span>{p.episode_count} 集</span>
                      <span className="dot">·</span>
                      <span>{p.duration}s / 集</span>
                      <span className="dot">·</span>
                      <span>{p.ratio}</span>
                      <span className="dot">·</span>
                      <span>{p.style}</span>
                    </div>
                    <div className="stat-row">
                      <span>
                        <b>{p.stats?.episodes ?? 0}</b> 集已建
                      </span>
                      <span>
                        <b>{p.stats?.shots ?? 0}</b> 分镜
                      </span>
                      <span>
                        <b>{p.stats?.characters ?? 0}</b> 角色
                      </span>
                    </div>
                  </div>
                </article>
              );
            })}
            <button className="project-new" onClick={() => setOpen(true)}>
              <span>+</span>
              新建短剧项目
            </button>
          </div>
        )}
      </section>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="新建短剧项目"
        subtitle="先定一个基本盘，后面每一步都可以再改。"
      >
        <Field label="剧名">
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="例如：雨夜翻盘"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") create();
            }}
          />
        </Field>
        <div className="grid two">
          <Field label="题材">
            <select value={form.genre} onChange={(e) => setForm({ ...form, genre: e.target.value })}>
              {GENRES.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </Field>
          <Field label="画面风格">
            <select value={form.style} onChange={(e) => setForm({ ...form, style: e.target.value })}>
              {STYLES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </Field>
          <Field label="画幅">
            <select value={form.ratio} onChange={(e) => setForm({ ...form, ratio: e.target.value })}>
              {RATIOS.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </Field>
          <Field label="集数">
            <input
              type="number"
              min={1}
              max={60}
              value={form.episode_count}
              onChange={(e) => setForm({ ...form, episode_count: Number(e.target.value) })}
            />
          </Field>
          <Field label="单集时长（秒）" hint="短剧一般 60–120 秒">
            <input
              type="number"
              min={15}
              max={600}
              step={15}
              value={form.duration}
              onChange={(e) => setForm({ ...form, duration: Number(e.target.value) })}
            />
          </Field>
        </div>
        <div className="modal-actions">
          <button className="btn ghost" onClick={() => setOpen(false)}>
            取消
          </button>
          <button className="btn primary" onClick={create} disabled={saving}>
            {saving && <Spinner />}
            创建并进入工作台
          </button>
        </div>
      </Modal>
    </div>
  );
}
