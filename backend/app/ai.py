"""BYOK（自带密钥）AI 代理。

平台不内置任何额度，也不售卖积分：密钥只保存在用户浏览器里，
每个请求通过 X-AI-Config 头随请求发送，后端用完即弃、不落库。
"""

import base64
import json
import re
from urllib.parse import quote

import httpx

TIMEOUT = httpx.Timeout(120.0, connect=20.0)


class AIError(Exception):
    pass


def decode_config(header_value: str | None) -> dict:
    cfg = {
        "mode": "demo",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "text_model": "gpt-4o-mini",
        "image_model": "gpt-image-1",
        "image_quality": "high",
        "tts_model": "gpt-4o-mini-tts",
        "tts_voice": "alloy",
        "video_model": "sora-2",
    }
    if not header_value:
        return cfg
    try:
        raw = base64.b64decode(header_value).decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if v is not None})
    except Exception:
        return cfg
    if not cfg.get("api_key"):
        cfg["mode"] = "demo"
    if cfg.get("mode") not in ("demo", "byok"):
        cfg["mode"] = "byok" if cfg.get("api_key") else "demo"
    return cfg


def is_demo(cfg: dict) -> bool:
    return cfg.get("mode") != "byok" or not cfg.get("api_key")


def _headers(cfg: dict) -> dict:
    return {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }


def _endpoint(cfg: dict, path: str) -> str:
    base = (cfg.get("base_url") or "").rstrip("/")
    if not base:
        raise AIError("未填写 API Base URL")
    return f"{base}/{path.lstrip('/')}"


def _post(cfg: dict, path: str, payload: dict, retries: int = 0) -> dict:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(_endpoint(cfg, path), headers=_headers(cfg), json=payload)
    except httpx.HTTPError as exc:
        raise AIError(f"网络请求失败：{exc}") from exc
    if resp.status_code >= 400 and retries > 0:
        return _post(cfg, path, payload, retries - 1)
    if resp.status_code >= 400:
        raise AIError(f"上游返回 {resp.status_code}：{resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise AIError("上游返回了无法解析的内容") from exc


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    candidates = []
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])
    first_a = text.find("[")
    last_a = text.rfind("]")
    if first_a != -1 and last_a > first_a:
        candidates.append(text[first_a : last_a + 1])
    candidates.append(text)
    for item in candidates:
        try:
            return json.loads(item)
        except json.JSONDecodeError:
            continue
    raise AIError("模型返回的 JSON 无法解析")


def chat_json(cfg: dict, system: str, user: str):
    payload = {
        "model": cfg.get("text_model") or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.85,
    }
    try:
        data = _post(cfg, "chat/completions", {**payload, "response_format": {"type": "json_object"}}, retries=1)
    except AIError:
        data = _post(cfg, "chat/completions", payload)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError("上游响应缺少内容字段") from exc
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return _extract_json(content)


def chat_text(cfg: dict, system: str, user: str) -> str:
    payload = {
        "model": cfg.get("text_model") or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.8,
    }
    data = _post(cfg, "chat/completions", payload)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError("上游响应缺少内容字段") from exc
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content.strip()


def image_size(ratio: str) -> str:
    # gpt-image-1 仅支持 1024x1024 / 1024x1536 / 1536x1024 / auto
    return {
        "9:16": "1024x1536",
        "16:9": "1536x1024",
        "4:3": "1536x1024",
        "1:1": "1024x1024",
    }.get(ratio, "1024x1536")


def generate_image(cfg: dict, prompt: str, ratio: str = "9:16") -> bytes:
    payload = {
        "model": cfg.get("image_model") or "gpt-image-1",
        "prompt": prompt,
        "size": image_size(ratio),
        "n": 1,
        "quality": cfg.get("image_quality") or "high",
    }
    # 不传 response_format：gpt-image-1 固定返回 b64_json（也不接受该参数），
    # DALL-E / 中转默认返回 url，下方解析同时兼容两种返回。
    data = _post(cfg, "images/generations", payload, retries=1)
    items = data.get("data") or []
    if not items:
        raise AIError("图像接口没有返回结果")
    item = items[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = client.get(item["url"])
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPError as exc:
            raise AIError(f"下载生成图片失败：{exc}") from exc
    raise AIError("图像接口返回格式不支持")


def generate_speech(cfg: dict, text: str) -> bytes:
    payload = {
        "model": cfg.get("tts_model") or "gpt-4o-mini-tts",
        "voice": cfg.get("tts_voice") or "alloy",
        "input": text,
        "response_format": "mp3",
    }
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(_endpoint(cfg, "audio/speech"), headers=_headers(cfg), json=payload)
    except httpx.HTTPError as exc:
        raise AIError(f"网络请求失败：{exc}") from exc
    if resp.status_code >= 400:
        raise AIError(f"语音接口返回 {resp.status_code}：{resp.text[:300]}")
    return resp.content


def video_size(ratio: str) -> str:
    # Sora 式接口目前只支持竖屏 720x1280 与横屏 1280x720
    return "1280x720" if ratio in ("16:9", "4:3") else "720x1280"


def video_seconds(duration: float) -> str:
    # 上游只接受 4 / 8 / 12 秒，按镜头时长就近取档
    if duration <= 6:
        return "4"
    if duration <= 10:
        return "8"
    return "12"


def _get(cfg: dict, path: str, timeout: float = 30.0) -> dict:
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
            resp = client.get(_endpoint(cfg, path), headers=_headers(cfg))
    except httpx.HTTPError as exc:
        raise AIError(f"网络请求失败：{exc}") from exc
    if resp.status_code >= 400:
        raise AIError(f"上游返回 {resp.status_code}：{resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise AIError("上游返回了无法解析的内容") from exc


def create_video(cfg: dict, prompt: str, duration: float = 8.0, ratio: str = "9:16") -> dict:
    payload = {
        "model": cfg.get("video_model") or "sora-2",
        "prompt": prompt[:2000],
        "seconds": video_seconds(duration),
        "size": video_size(ratio),
    }
    return _post(cfg, "videos", payload)


def get_video(cfg: dict, job_id: str) -> dict:
    return _get(cfg, f"videos/{quote(job_id, safe='')}")


def download_video(cfg: dict, job_id: str, url: str = "") -> bytes:
    target = url or _endpoint(cfg, f"videos/{quote(job_id, safe='')}/content")
    headers = {} if url else _headers(cfg)
    try:
        with httpx.Client(timeout=httpx.Timeout(180.0, connect=20.0), follow_redirects=True) as client:
            resp = client.get(target, headers=headers)
    except httpx.HTTPError as exc:
        raise AIError(f"下载生成视频失败：{exc}") from exc
    if resp.status_code >= 400:
        raise AIError(f"下载生成视频失败（{resp.status_code}）：{resp.text[:200]}")
    if not resp.content:
        raise AIError("视频接口返回了空内容")
    return resp.content


def test_config(cfg: dict) -> dict:
    if is_demo(cfg):
        return {"ok": True, "mode": "demo", "message": "当前为演示模式，无需密钥即可使用"}
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            resp = client.get(_endpoint(cfg, "models"), headers=_headers(cfg))
        if resp.status_code >= 400:
            raise AIError(f"返回 {resp.status_code}：{resp.text[:200]}")
        data = resp.json()
        models = data.get("data") if isinstance(data, dict) else None
        return {
            "ok": True,
            "mode": "byok",
            "message": f"连接成功，可用模型 {len(models) if isinstance(models, list) else '未知'} 个",
        }
    except (AIError, httpx.HTTPError) as exc:
        return {"ok": False, "mode": "byok", "message": str(exc)}
