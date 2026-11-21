import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("SHORTPLAY_DATA_DIR") or os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(DATA_DIR, "assets")
DB_PATH = os.path.join(DATA_DIR, "studio.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    genre TEXT NOT NULL DEFAULT '都市逆袭',
    style TEXT NOT NULL DEFAULT '真人写实',
    ratio TEXT NOT NULL DEFAULT '9:16',
    episode_count INTEGER NOT NULL DEFAULT 12,
    duration INTEGER NOT NULL DEFAULT 90,
    logline TEXT NOT NULL DEFAULT '',
    synopsis TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT '',
    age TEXT NOT NULL DEFAULT '',
    appearance TEXT NOT NULL DEFAULT '',
    personality TEXT NOT NULL DEFAULT '',
    arc TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    image_asset TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    script TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '待生成',
    final_asset TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shots (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    shot_type TEXT NOT NULL DEFAULT '中景',
    camera TEXT NOT NULL DEFAULT '固定',
    duration REAL NOT NULL DEFAULT 4,
    location TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    dialogue TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    image_asset TEXT NOT NULL DEFAULT '',
    video_asset TEXT NOT NULL DEFAULT '',
    audio_asset TEXT NOT NULL DEFAULT '',
    video_job TEXT NOT NULL DEFAULT '',
    video_status TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'image',
    name TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL DEFAULT '',
    mime TEXT NOT NULL DEFAULT 'application/octet-stream',
    source TEXT NOT NULL DEFAULT 'upload',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id);
CREATE INDEX IF NOT EXISTS idx_episodes_project ON episodes(project_id);
CREATE INDEX IF NOT EXISTS idx_shots_episode ON shots(episode_id);
CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    os.makedirs(ASSET_DIR, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)
        # 老库平滑升级：补上视频任务字段
        columns = {row[1] for row in conn.execute("PRAGMA table_info(shots)").fetchall()}
        for name in ("video_job", "video_status"):
            if name not in columns:
                conn.execute(f"ALTER TABLE shots ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        # 老库平滑升级：补上整集成片字段
        ep_columns = {row[1] for row in conn.execute("PRAGMA table_info(episodes)").fetchall()}
        if "final_asset" not in ep_columns:
            conn.execute("ALTER TABLE episodes ADD COLUMN final_asset TEXT NOT NULL DEFAULT ''")
