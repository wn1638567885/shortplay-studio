import csv
import io
import json
import os
import re

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import ai, demo
from .db import ASSET_DIR, DATA_DIR, db, init_db, new_id, now_iso

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.normpath(os.path.join(APP_DIR, "..", "frontend", "dist"))

app = FastAPI(title="剧作工坊 ShortPlay Studio", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def cfg_of(request: Request) -> dict:
    return ai.decode_config(request.headers.get("X-AI-Config"))


def _project_or_404(conn, pid: str) -> dict:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not row:
        raise HTTPException(404, "项目不存在")
    return dict(row)


def _episode_or_404(conn, eid: str) -> dict:
    row = conn.execute("SELECT * FROM episodes WHERE id = ?", (eid,)).fetchone()
    if not row:
        raise HTTPException(404, "剧集不存在")
    return dict(row)


def _shot_or_404(conn, sid: str) -> dict:
    row = conn.execute("SELECT * FROM shots WHERE id = ?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "分镜不存在")
    return dict(row)


def _asset_dict(row) -> dict:
    row = dict(row)
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "kind": row["kind"],
        "name": row["name"],
        "mime": row["mime"],
        "source": row["source"],
        "url": f"/api/assets/{row['id']}/raw",
        "created_at": row["created_at"],
    }


def _save_asset(conn, project_id: str, kind: str, name: str, data: bytes, ext: str, mime: str, source: str) -> dict:
    aid = new_id("as")
    filename = f"{aid}.{ext}"
    with open(os.path.join(ASSET_DIR, filename), "wb") as fh:
        fh.write(data)
    conn.execute(
        "INSERT INTO assets (id, project_id, kind, name, filename, mime, source, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (aid, project_id, kind, name, filename, mime, source, now_iso()),
    )
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (aid,)).fetchone()
    return _asset_dict(row)


def _char_dict(row) -> dict:
    row = dict(row)
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "name": row["name"],
        "role": row["role"],
        "gender": row["gender"],
        "age": row["age"],
        "appearance": row["appearance"],
        "personality": row["personality"],
        "arc": row["arc"],
        "prompt": row["prompt"],
        "image_asset": row["image_asset"],
        "image_url": f"/api/assets/{row['image_asset']}/raw" if row["image_asset"] else "",
    }


def _shot_dict(row) -> dict:
    row = dict(row)
    return {
        "id": row["id"],
        "episode_id": row["episode_id"],
        "idx": row["idx"],
        "shot_type": row["shot_type"],
        "camera": row["camera"],
        "duration": row["duration"],
        "location": row["location"],
        "description": row["description"],
        "dialogue": row["dialogue"],
        "prompt": row["prompt"],
        "image_asset": row["image_asset"],
        "video_asset": row["video_asset"],
        "audio_asset": row["audio_asset"],
        "image_url": f"/api/assets/{row['image_asset']}/raw" if row["image_asset"] else "",
        "video_url": f"/api/assets/{row['video_asset']}/raw" if row["video_asset"] else "",
        "audio_url": f"/api/assets/{row['audio_asset']}/raw" if row["audio_asset"] else "",
    }


def _project_dict(row) -> dict:
    row = dict(row)
    cover = row.pop("cover_id", None)
    return {
        **row,
        "cover_url": f"/api/assets/{cover}/raw" if cover else "",
    }


def _detail(conn, pid: str) -> dict:
    project = _project_or_404(conn, pid)
    characters = [_char_dict(r) for r in conn.execute(
        "SELECT * FROM characters WHERE project_id = ? ORDER BY created_at", (pid,)
    ).fetchall()]
    episodes = []
    for ep in conn.execute(
        "SELECT * FROM episodes WHERE project_id = ? ORDER BY idx", (pid,)
    ).fetchall():
        ep = dict(ep)
        shots = [_shot_dict(r) for r in conn.execute(
            "SELECT * FROM shots WHERE episode_id = ? ORDER BY idx", (ep["id"],)
        ).fetchall()]
        episodes.append({**ep, "shots": shots, "shot_count": len(shots)})
    assets = [_asset_dict(r) for r in conn.execute(
        "SELECT * FROM assets WHERE project_id = ? ORDER BY created_at DESC", (pid,)
    ).fetchall()]
    stats = {
        "episodes": len(episodes),
        "shots": sum(len(e["shots"]) for e in episodes),
        "characters": len(characters),
        "assets": len(assets),
        "scripts": sum(1 for e in episodes if e["script"]),
    }
    return {"project": project, "characters": characters, "episodes": episodes, "assets": assets, "stats": stats}


def _touch(conn, pid: str) -> None:
    conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now_iso(), pid))


def _replace_outline(conn, project: dict, data: dict) -> None:
    conn.execute(
        "UPDATE projects SET logline = ?, synopsis = ?, updated_at = ? WHERE id = ?",
        (data.get("logline", ""), data.get("synopsis", ""), now_iso(), project["id"]),
    )
    conn.execute("DELETE FROM characters WHERE project_id = ?", (project["id"],))
    for c in data.get("characters", []):
        conn.execute(
            "INSERT INTO characters (id, project_id, name, role, gender, age, appearance, personality, arc, prompt, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("ch"), project["id"], c.get("name", ""), c.get("role", ""),
                c.get("gender", ""), c.get("age", ""), c.get("appearance", ""),
                c.get("personality", ""), c.get("arc", ""), c.get("prompt", ""), now_iso(),
            ),
        )

    count = int(project["episode_count"])
    existing = {e["idx"]: e for e in conn.execute(
        "SELECT * FROM episodes WHERE project_id = ?", (project["id"],)
    ).fetchall()}
    incoming = data.get("episodes", [])
    for i in range(1, count + 1):
        item = incoming[i - 1] if i - 1 < len(incoming) else {}
        title = item.get("title") or f"第{i}集"
        summary = item.get("summary") or ""
        if i in existing:
            conn.execute(
                "UPDATE episodes SET title = ?, summary = ? WHERE id = ?",
                (title, summary, existing[i]["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO episodes (id, project_id, idx, title, summary, script, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, '', '待生成', ?)",
                (new_id("ep"), project["id"], i, title, summary, now_iso()),
            )
    for idx, ep in existing.items():
        if idx > count:
            conn.execute("DELETE FROM shots WHERE episode_id = ?", (ep["id"],))
            conn.execute("DELETE FROM episodes WHERE id = ?", (ep["id"],))


@app.get("/api/health")
def health():
    return {"ok": True, "genres": demo.GENRE_NAMES, "styles": demo.STYLES, "ratios": demo.RATIOS}


@app.get("/api/projects")
def list_projects():
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.*,
              (SELECT COUNT(*) FROM episodes e WHERE e.project_id = p.id) AS episode_total,
              (SELECT COUNT(*) FROM shots s JOIN episodes e ON s.episode_id = e.id
                 WHERE e.project_id = p.id) AS shot_total,
              (SELECT COUNT(*) FROM characters c WHERE c.project_id = p.id) AS character_total,
              (SELECT id FROM assets a WHERE a.project_id = p.id AND a.kind = 'image'
                 AND a.source <> 'demo' ORDER BY a.created_at DESC LIMIT 1) AS cover_id
            FROM projects p ORDER BY p.updated_at DESC
            """
        ).fetchall()
        items = []
        for row in rows:
            item = _project_dict(row)
            item["stats"] = {
                "episodes": row["episode_total"],
                "shots": row["shot_total"],
                "characters": row["character_total"],
            }
            items.append(item)
        return {"items": items}


@app.post("/api/projects")
def create_project(payload: dict = Body(...)):
    title = (payload.get("title") or "").strip() or "未命名短剧"
    genre = payload.get("genre") or "都市逆袭"
    style = payload.get("style") or "真人写实"
    ratio = payload.get("ratio") or "9:16"
    try:
        episode_count = max(1, min(60, int(payload.get("episode_count") or 12)))
    except (TypeError, ValueError):
        episode_count = 12
    try:
        duration = max(15, min(600, int(payload.get("duration") or 90)))
    except (TypeError, ValueError):
        duration = 90
    pid = new_id("pj")
    ts = now_iso()
    with db() as conn:
        conn.execute(
            "INSERT INTO projects (id, title, genre, style, ratio, episode_count, duration, logline, synopsis, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, '', '', ?, ?)",
            (pid, title, genre, style, ratio, episode_count, duration, ts, ts),
        )
        return _detail(conn, pid)


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    with db() as conn:
        return _detail(conn, pid)


@app.patch("/api/projects/{pid}")
def update_project(pid: str, payload: dict = Body(...)):
    with db() as conn:
        project = _project_or_404(conn, pid)
        fields = {}
        for key in ("title", "genre", "style", "ratio", "logline", "synopsis"):
            if key in payload and payload[key] is not None:
                fields[key] = str(payload[key])
        if "episode_count" in payload:
            try:
                fields["episode_count"] = max(1, min(60, int(payload["episode_count"])))
            except (TypeError, ValueError):
                pass
        if "duration" in payload:
            try:
                fields["duration"] = max(15, min(600, int(payload["duration"])))
            except (TypeError, ValueError):
                pass
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE projects SET {sets}, updated_at = ? WHERE id = ?",
                         (*fields.values(), now_iso(), pid))
            if "episode_count" in fields:
                keep = fields["episode_count"]
                extra = conn.execute(
                    "SELECT * FROM episodes WHERE project_id = ? AND idx > ?", (pid, keep)
                ).fetchall()
                for ep in extra:
                    conn.execute("DELETE FROM shots WHERE episode_id = ?", (ep["id"],))
                    conn.execute("DELETE FROM episodes WHERE id = ?", (ep["id"],))
        _touch(conn, pid)
        return _detail(conn, pid)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    with db() as conn:
        _project_or_404(conn, pid)
        episode_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM episodes WHERE project_id = ?", (pid,)
        ).fetchall()]
        for eid in episode_ids:
            conn.execute("DELETE FROM shots WHERE episode_id = ?", (eid,))
        conn.execute("DELETE FROM episodes WHERE project_id = ?", (pid,))
        conn.execute("DELETE FROM characters WHERE project_id = ?", (pid,))
        assets = conn.execute("SELECT filename FROM assets WHERE project_id = ?", (pid,)).fetchall()
        for a in assets:
            try:
                os.remove(os.path.join(ASSET_DIR, a["filename"]))
            except OSError:
                pass
        conn.execute("DELETE FROM assets WHERE project_id = ?", (pid,))
        conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    return {"ok": True}


OUTLINE_SYSTEM = (
    "你是一位资深短剧编剧，擅长强钩子、快节奏、每集结尾留扣。"
    "只输出合法 JSON，不要任何解释性文字。"
)


def _normalize_outline(data, project: dict) -> dict:
    fallback = demo.outline(project)
    if not isinstance(data, dict):
        return fallback
    count = int(project["episode_count"])
    chars = data.get("characters")
    if not isinstance(chars, list) or not chars:
        chars = fallback["characters"]
    episodes = data.get("episodes")
    if not isinstance(episodes, list):
        episodes = fallback["episodes"]
    normalized = []
    for i in range(1, count + 1):
        raw = episodes[i - 1] if i - 1 < len(episodes) and isinstance(episodes[i - 1], dict) else {}
        fb = fallback["episodes"][i - 1]
        normalized.append({
            "idx": i,
            "title": str(raw.get("title") or fb["title"]),
            "summary": str(raw.get("summary") or fb["summary"]),
        })
    return {
        "logline": str(data.get("logline") or fallback["logline"]),
        "synopsis": str(data.get("synopsis") or fallback["synopsis"]),
        "characters": [
            {
                "name": str(c.get("name") or ""),
                "role": str(c.get("role") or ""),
                "gender": str(c.get("gender") or ""),
                "age": str(c.get("age") or ""),
                "appearance": str(c.get("appearance") or ""),
                "personality": str(c.get("personality") or ""),
                "arc": str(c.get("arc") or ""),
                "prompt": str(c.get("prompt") or ""),
            }
            for c in chars if isinstance(c, dict)
        ],
        "episodes": normalized,
    }


@app.post("/api/projects/{pid}/generate/outline")
def generate_outline(pid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        project = _project_or_404(conn, pid)
        warning = None
        source = "demo"
        data = None
        if not ai.is_demo(cfg):
            user = f"""请为下面这部短剧输出创作方案：
剧名：{project['title']}
题材：{project['genre']}
画面风格：{project['style']}
画幅：{project['ratio']}
集数：{project['episode_count']}
单集时长：{project['duration']} 秒

严格输出 JSON，结构如下：
{{
  "logline": "一句话故事线（40字内）",
  "synopsis": "故事简介（150字内）",
  "characters": [
    {{"name": "角色名", "role": "身份/定位（如 男主·落魄外卖员）", "gender": "男/女",
      "age": "27", "appearance": "外貌细节", "personality": "性格",
      "arc": "人物弧光", "prompt": "用于AI绘图的形象提示词，含风格与光影"}}
  ],
  "episodes": [{{"title": "本集短标题", "summary": "本集剧情摘要（60字内）"}}]
}}
要求：角色 3-4 个；episodes 必须正好 {project['episode_count']} 集；每集结尾要有钩子。"""
            try:
                data = _normalize_outline(ai.chat_json(cfg, OUTLINE_SYSTEM, user), project)
                source = "ai"
            except ai.AIError as exc:
                warning = f"AI 生成失败，已使用内置演示模板：{exc}"
        if data is None:
            data = _normalize_outline(demo.outline(project), project)
        _replace_outline(conn, project, data)
        payload = _detail(conn, pid)
        return {**payload, "source": source, "warning": warning}


@app.post("/api/projects/{pid}/generate/characters")
def generate_characters(pid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        project = _project_or_404(conn, pid)
        warning = None
        source = "demo"
        chars = None
        if not ai.is_demo(cfg):
            user = f"""为短剧《{project['title']}》（题材：{project['genre']}，风格：{project['style']}）设计 3 个核心角色。
输出 JSON：{{"characters": [{{"name","role","gender","age","appearance","personality","arc","prompt"}}]}}
prompt 要能直接用于 AI 绘图，包含人物外貌、服装、光线、风格。"""
            try:
                data = ai.chat_json(cfg, OUTLINE_SYSTEM, user)
                raw = data.get("characters") if isinstance(data, dict) else data
                if isinstance(raw, list) and raw:
                    chars = [
                        {
                            "name": str(c.get("name") or ""),
                            "role": str(c.get("role") or ""),
                            "gender": str(c.get("gender") or ""),
                            "age": str(c.get("age") or ""),
                            "appearance": str(c.get("appearance") or ""),
                            "personality": str(c.get("personality") or ""),
                            "arc": str(c.get("arc") or ""),
                            "prompt": str(c.get("prompt") or ""),
                        }
                        for c in raw if isinstance(c, dict)
                    ]
                    source = "ai"
            except ai.AIError as exc:
                warning = f"AI 生成失败，已使用内置演示模板：{exc}"
        if chars is None:
            chars = demo.characters(project)
        conn.execute("DELETE FROM characters WHERE project_id = ?", (pid,))
        for c in chars:
            conn.execute(
                "INSERT INTO characters (id, project_id, name, role, gender, age, appearance, personality, arc, prompt, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("ch"), pid, c["name"], c["role"], c["gender"], c["age"],
                 c["appearance"], c["personality"], c["arc"], c["prompt"], now_iso()),
            )
        _touch(conn, pid)
        payload = _detail(conn, pid)
        return {**payload, "source": source, "warning": warning}


@app.patch("/api/episodes/{eid}")
def update_episode(eid: str, payload: dict = Body(...)):
    with db() as conn:
        episode = _episode_or_404(conn, eid)
        fields = {}
        for key in ("title", "summary", "script", "status"):
            if key in payload and payload[key] is not None:
                fields[key] = str(payload[key])
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE episodes SET {sets} WHERE id = ?", (*fields.values(), eid))
            _touch(conn, episode["project_id"])
        return _episode_or_404(conn, eid)


@app.post("/api/episodes/{eid}/generate/script")
def generate_script(eid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        episode = _episode_or_404(conn, eid)
        project = _project_or_404(conn, episode["project_id"])
        characters = [dict(r) for r in conn.execute(
            "SELECT * FROM characters WHERE project_id = ?", (project["id"],)
        ).fetchall()]
        warning = None
        source = "demo"
        content = None
        if not ai.is_demo(cfg):
            cast = "、".join(f"{c['name']}（{c['role']}）" for c in characters) or "按剧情需要"
            user = f"""为短剧《{project['title']}》（{project['genre']}，{project['style']}，单集约 {project['duration']} 秒）写第 {episode['idx']} 集剧本。
本集标题：{episode['title']}
本集摘要：{episode['summary']}
主要角色：{cast}

要求：
1. 输出纯 Markdown 剧本，不要解释、不要代码块围栏。
2. 分 4-5 场，标注场次、地点、时间、内/外景。
3. 台词要短、有冲突，符合竖屏短剧节奏。
4. 结尾留强钩子，标注【本集钩子】。"""
            try:
                content = ai.chat_text(cfg, OUTLINE_SYSTEM.replace("只输出合法 JSON，不要任何解释性文字。", ""), user)
                source = "ai"
            except ai.AIError as exc:
                warning = f"AI 生成失败，已使用内置演示模板：{exc}"
        if not content:
            content = demo.script(project, episode)
        conn.execute(
            "UPDATE episodes SET script = ?, status = '已生成剧本' WHERE id = ?", (content, eid)
        )
        _touch(conn, project["id"])
        payload = _episode_or_404(conn, eid)
        return {"episode": payload, "source": source, "warning": warning}


@app.patch("/api/shots/{sid}")
def update_shot(sid: str, payload: dict = Body(...)):
    with db() as conn:
        shot = _shot_or_404(conn, sid)
        allowed = ("shot_type", "camera", "location", "description", "dialogue", "prompt")
        fields = {k: str(payload[k]) for k in allowed if k in payload and payload[k] is not None}
        if "duration" in payload:
            try:
                fields["duration"] = float(payload["duration"])
            except (TypeError, ValueError):
                pass
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE shots SET {sets} WHERE id = ?", (*fields.values(), sid))
            episode = _episode_or_404(conn, shot["episode_id"])
            _touch(conn, episode["project_id"])
        return _shot_dict(_shot_or_404_conn(conn, sid))


def _shot_or_404_conn(conn, sid: str):
    row = conn.execute("SELECT * FROM shots WHERE id = ?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "分镜不存在")
    return row


@app.post("/api/episodes/{eid}/generate/storyboard")
def generate_storyboard(eid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        episode = _episode_or_404(conn, eid)
        project = _project_or_404(conn, episode["project_id"])
        warning = None
        source = "demo"
        shots = None
        if not ai.is_demo(cfg):
            user = f"""为短剧《{project['title']}》（{project['genre']}，{project['style']}，{project['ratio']} 竖屏）第 {episode['idx']} 集拆分镜。
本集标题：{episode['title']}
本集摘要：{episode['summary']}

输出 JSON：{{"shots": [{{"shot_type": "景别", "camera": "运镜", "duration": 4.5,
"location": "地点", "description": "画面内容", "dialogue": "该镜头台词，可空",
"prompt": "AI 绘图提示词，含风格、光线、人物一致性要求"}}]}}
要求 8-12 个镜头，总时长贴近 {project['duration']} 秒，开头有钩子，结尾留悬念。"""
            try:
                data = ai.chat_json(cfg, OUTLINE_SYSTEM, user)
                raw = data.get("shots") if isinstance(data, dict) else data
                if isinstance(raw, list) and raw:
                    shots = []
                    for i, s in enumerate(raw, start=1):
                        if not isinstance(s, dict):
                            continue
                        try:
                            dur = float(s.get("duration") or 4)
                        except (TypeError, ValueError):
                            dur = 4.0
                        shots.append({
                            "idx": i,
                            "shot_type": str(s.get("shot_type") or "中景"),
                            "camera": str(s.get("camera") or "固定"),
                            "duration": dur,
                            "location": str(s.get("location") or ""),
                            "description": str(s.get("description") or ""),
                            "dialogue": str(s.get("dialogue") or ""),
                            "prompt": str(s.get("prompt") or ""),
                        })
                    if shots:
                        source = "ai"
                    else:
                        shots = None
            except ai.AIError as exc:
                warning = f"AI 生成失败，已使用内置演示模板：{exc}"
        if not shots:
            shots = demo.storyboard(project, episode)
        conn.execute("DELETE FROM shots WHERE episode_id = ?", (eid,))
        for s in shots:
            conn.execute(
                "INSERT INTO shots (id, episode_id, idx, shot_type, camera, duration, location,"
                " description, dialogue, prompt, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("sh"), eid, s["idx"], s["shot_type"], s["camera"], s["duration"],
                 s["location"], s["description"], s["dialogue"], s["prompt"], now_iso()),
            )
        conn.execute("UPDATE episodes SET status = '已分镜' WHERE id = ?", (eid,))
        _touch(conn, project["id"])
        episode = _episode_or_404(conn, eid)
        shots_out = [_shot_dict(r) for r in conn.execute(
            "SELECT * FROM shots WHERE episode_id = ? ORDER BY idx", (eid,)
        ).fetchall()]
        return {**episode, "shots": shots_out, "shot_count": len(shots_out),
                "source": source, "warning": warning}


def _demo_cover(project: dict, title: str, subtitle: str, badge: str) -> tuple[bytes, str, str]:
    genre = demo.GENRES.get(project.get("genre") or "", demo.GENRES["都市逆袭"])
    svg = demo.placeholder_svg(title, subtitle, genre["color"], project.get("ratio") or "9:16", badge)
    return svg.encode("utf-8"), "svg", "image/svg+xml"


def _detect_image(data: bytes) -> tuple[str, str]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if data[:2] == b"\xff\xd8":
        return "jpg", "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return "png", "image/png"


@app.post("/api/shots/{sid}/generate/image")
def generate_shot_image(sid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        shot = _shot_or_404(conn, sid)
        episode = _episode_or_404(conn, shot["episode_id"])
        project = _project_or_404(conn, episode["project_id"])
        warning = None
        source = "demo"
        prompt = shot["prompt"] or (
            f"{project['style']}，竖屏 {project['ratio']}，电影级画面，"
            f"{shot['shot_type']}，{shot['description']}"
        )
        if not ai.is_demo(cfg):
            try:
                data = ai.generate_image(cfg, prompt, project["ratio"])
                ext, mime = _detect_image(data)
                source = "ai"
            except ai.AIError as exc:
                warning = f"图像生成失败，已使用演示画面：{exc}"
                data = None
            if data is None:
                raw, ext, mime = _demo_cover(project, shot["shot_type"], shot["description"], "分镜示意")
                data = raw
        else:
            raw, ext, mime = _demo_cover(project, shot["shot_type"], shot["description"], "分镜示意")
            data = raw
        asset = _save_asset(conn, project["id"], "image", f"镜头{shot['idx']} · {shot['shot_type']}",
                            data, ext, mime, source)
        conn.execute("UPDATE shots SET image_asset = ? WHERE id = ?", (asset["id"], sid))
        _touch(conn, project["id"])
        return {"asset": asset, "shot": _shot_dict(_shot_or_404_conn(conn, sid)),
                "source": source, "warning": warning}


@app.post("/api/characters/{cid}/generate/image")
def generate_character_image(cid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        row = conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, "角色不存在")
        character = dict(row)
        project = _project_or_404(conn, character["project_id"])
        warning = None
        source = "demo"
        prompt = character["prompt"] or (
            f"{project['style']}，{character['gender']}性，{character['age']}岁，"
            f"{character['appearance']}，{character['personality']}，半身像，电影光效"
        )
        data = None
        if not ai.is_demo(cfg):
            try:
                data = ai.generate_image(cfg, prompt, project["ratio"])
                ext, mime = _detect_image(data)
                source = "ai"
            except ai.AIError as exc:
                warning = f"图像生成失败，已使用演示画面：{exc}"
                data = None
        if data is None:
            raw, ext, mime = _demo_cover(project, character["name"], character["appearance"], "角色设定")
            data = raw
        asset = _save_asset(conn, project["id"], "image", f"角色 · {character['name']}",
                            data, ext, mime, source)
        conn.execute("UPDATE characters SET image_asset = ? WHERE id = ?", (asset["id"], cid))
        _touch(conn, project["id"])
        return {"asset": asset, "character": _char_dict(
            conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone()),
            "source": source, "warning": warning}


@app.post("/api/shots/{sid}/generate/voice")
def generate_shot_voice(sid: str, request: Request):
    cfg = cfg_of(request)
    with db() as conn:
        shot = _shot_or_404(conn, sid)
        episode = _episode_or_404(conn, shot["episode_id"])
        project = _project_or_404(conn, episode["project_id"])
        if not shot["dialogue"]:
            raise HTTPException(400, "该镜头还没有台词")
        if ai.is_demo(cfg):
            raise HTTPException(400, "演示模式不调用云端语音。可用「浏览器朗读」免费试听台词。")
        try:
            data = ai.generate_speech(cfg, shot["dialogue"])
        except ai.AIError as exc:
            raise HTTPException(400, str(exc)) from exc
        asset = _save_asset(conn, project["id"], "audio", f"配音 · 镜头{shot['idx']}",
                            data, "mp3", "audio/mpeg", "ai")
        conn.execute("UPDATE shots SET audio_asset = ? WHERE id = ?", (asset["id"], sid))
        _touch(conn, project["id"])
        return {"asset": asset, "shot": _shot_dict(_shot_or_404_conn(conn, sid)), "source": "ai"}


@app.post("/api/shots/{sid}/upload")
async def upload_shot_asset(sid: str, file: UploadFile = File(...), kind: str = Form("video")):
    with db() as conn:
        shot = _shot_or_404(conn, sid)
        episode = _episode_or_404(conn, shot["episode_id"])
        project = _project_or_404(conn, episode["project_id"])
        data = await file.read()
        if len(data) > 300 * 1024 * 1024:
            raise HTTPException(400, "文件超过 300MB")
        ext = (file.filename or "file").rsplit(".", 1)[-1].lower()
        mime = file.content_type or "application/octet-stream"
        if kind not in ("image", "video", "audio"):
            kind = "video"
        _fix = {"jpeg": "jpg"}
        ext = _fix.get(ext, ext)
        asset = _save_asset(conn, project["id"], kind, file.filename or f"素材.{ext}",
                            data, ext, mime, "upload")
        column = {"image": "image_asset", "video": "video_asset", "audio": "audio_asset"}[kind]
        conn.execute(f"UPDATE shots SET {column} = ? WHERE id = ?", (asset["id"], sid))
        _touch(conn, project["id"])
        return {"asset": asset, "shot": _shot_dict(_shot_or_404_conn(conn, sid))}


@app.post("/api/assets/upload")
async def upload_asset(
    project_id: str = Form(...),
    kind: str = Form("other"),
    file: UploadFile = File(...),
):
    with db() as conn:
        _project_or_404(conn, project_id)
        data = await file.read()
        if len(data) > 300 * 1024 * 1024:
            raise HTTPException(400, "文件超过 300MB")
        ext = (file.filename or "file").rsplit(".", 1)[-1].lower() or "bin"
        if kind not in ("image", "video", "audio", "other"):
            kind = "other"
        asset = _save_asset(conn, project_id, kind, file.filename or f"素材.{ext}", data,
                            ext, file.content_type or "application/octet-stream", "upload")
        _touch(conn, project_id)
        return {"asset": asset}


@app.post("/api/characters")
def create_character(payload: dict = Body(...)):
    pid = payload.get("project_id")
    with db() as conn:
        project = _project_or_404(conn, pid)
        cid = new_id("ch")
        conn.execute(
            "INSERT INTO characters (id, project_id, name, role, gender, age, appearance, personality, arc, prompt, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, pid, payload.get("name") or "新角色", payload.get("role") or "",
             payload.get("gender") or "", payload.get("age") or "",
             payload.get("appearance") or "", payload.get("personality") or "",
             payload.get("arc") or "", payload.get("prompt") or "", now_iso()),
        )
        _touch(conn, project["id"])
        return _char_dict(conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone())


@app.patch("/api/characters/{cid}")
def update_character(cid: str, payload: dict = Body(...)):
    with db() as conn:
        row = conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, "角色不存在")
        fields = {k: str(payload[k]) for k in
                  ("name", "role", "gender", "age", "appearance", "personality", "arc", "prompt")
                  if k in payload and payload[k] is not None}
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE characters SET {sets} WHERE id = ?", (*fields.values(), cid))
            _touch(conn, row["project_id"])
        return _char_dict(conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone())


@app.get("/api/assets/{aid}/raw")
def asset_raw(aid: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (aid,)).fetchone()
        if not row:
            raise HTTPException(404, "素材不存在")
        path = os.path.join(ASSET_DIR, row["filename"])
        if not os.path.exists(path):
            raise HTTPException(404, "素材文件已丢失")
        return FileResponse(path, media_type=row["mime"], filename=row["name"])


@app.delete("/api/assets/{aid}")
def delete_asset(aid: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (aid,)).fetchone()
        if not row:
            raise HTTPException(404, "素材不存在")
        for column in ("image_asset", "video_asset", "audio_asset"):
            conn.execute(f"UPDATE shots SET {column} = '' WHERE {column} = ?", (aid,))
        conn.execute("UPDATE characters SET image_asset = '' WHERE image_asset = ?", (aid,))
        conn.execute("DELETE FROM assets WHERE id = ?", (aid,))
        try:
            os.remove(os.path.join(ASSET_DIR, row["filename"]))
        except OSError:
            pass
        _touch(conn, row["project_id"])
    return {"ok": True}


def _export_markdown(detail: dict) -> str:
    p = detail["project"]
    lines = [
        f"# {p['title']}",
        "",
        f"> {p['genre']} ｜ {p['style']} ｜ {p['ratio']} ｜ {p['episode_count']} 集 × {p['duration']}s",
        "",
        "## 一句话故事线",
        p["logline"] or "（未生成）",
        "",
        "## 故事简介",
        p["synopsis"] or "（未生成）",
        "",
        "## 角色设定",
        "",
    ]
    for c in detail["characters"]:
        lines += [
            f"### {c['name']} · {c['role']}",
            f"- 性别 / 年龄：{c['gender']} / {c['age']}",
            f"- 外貌：{c['appearance']}",
            f"- 性格：{c['personality']}",
            f"- 弧光：{c['arc']}",
            f"- 形象提示词：{c['prompt']}",
            "",
        ]
    for ep in detail["episodes"]:
        lines += [f"## 第{ep['idx']}集 · {ep['title']}", "", f"**摘要：** {ep['summary']}", ""]
        if ep["script"]:
            lines += [ep["script"], ""]
        if ep["shots"]:
            lines += ["### 分镜表", "", "| # | 景别 | 运镜 | 时长 | 画面 | 台词 |", "| --- | --- | --- | --- | --- | --- |"]
            for s in ep["shots"]:
                desc = s["description"].replace("|", "／").replace("\n", " ")
                dlg = s["dialogue"].replace("|", "／").replace("\n", " ")
                lines.append(f"| {s['idx']} | {s['shot_type']} | {s['camera']} | {s['duration']}s | {desc} | {dlg} |")
            lines.append("")
    return "\n".join(lines)


def _export_csv(detail: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["集数", "镜头", "景别", "运镜", "时长(秒)", "场景", "画面", "台词", "绘图提示词"])
    for ep in detail["episodes"]:
        for s in ep["shots"]:
            writer.writerow([ep["idx"], s["idx"], s["shot_type"], s["camera"], s["duration"],
                             s["location"], s["description"], s["dialogue"], s["prompt"]])
    return "\ufeff" + buf.getvalue()


@app.get("/api/projects/{pid}/export")
def export_project(pid: str, format: str = "md"):
    with db() as conn:
        detail = _detail(conn, pid)
    fmt = (format or "md").lower()
    if fmt == "csv":
        content, media, ext = _export_csv(detail), "text/csv; charset=utf-8", "csv"
    elif fmt == "json":
        content, media, ext = json.dumps(detail, ensure_ascii=False, indent=2), "application/json; charset=utf-8", "json"
    else:
        content, media, ext = _export_markdown(detail), "text/markdown; charset=utf-8", "md"
    filename = f"shortplay-{pid}.{ext}"
    return _attachment(content, media, filename)


def _attachment(content: str, media: str, filename: str):
    from fastapi.responses import Response

    return Response(
        content=content.encode("utf-8"),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/ai/test")
def ai_test(request: Request):
    return ai.test_config(cfg_of(request))


# ---------- 静态前端（构建后单端口运行） ----------
if os.path.isdir(os.path.join(DIST_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="static")


@app.get("/{full_path:path}")
def spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "接口不存在")
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index):
        candidate = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.isfile(candidate) and not full_path.startswith("api"):
            return FileResponse(candidate)
        return FileResponse(index)
    return JSONResponse(
        {"detail": "前端尚未构建。开发模式请访问 Vite 端口 5173，或先执行 npm run build。"},
        status_code=404,
    )
