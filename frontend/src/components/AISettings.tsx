import { useEffect, useState } from "react";
import { apiClient, getAI, setAI } from "../api";
import type { AIConfig } from "../types";
import { Field, Modal, Spinner } from "../ui";

const PRESETS = [
  {
    name: "OpenAI",
    base_url: "https://api.openai.com/v1",
    text_model: "gpt-4o-mini",
    image_model: "gpt-image-1",
    tts_model: "gpt-4o-mini-tts",
  },
  {
    name: "DeepSeek（文本）",
    base_url: "https://api.deepseek.com/v1",
    text_model: "deepseek-chat",
    image_model: "gpt-image-1",
    tts_model: "gpt-4o-mini-tts",
  },
  {
    name: "自定义中转",
    base_url: "https://your-proxy.example.com/v1",
    text_model: "gpt-4o-mini",
    image_model: "gpt-image-1",
    tts_model: "gpt-4o-mini-tts",
  },
];

export function AISettings({
  open,
  onClose,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: (config: AIConfig) => void;
}) {
  const [config, setConfig] = useState<AIConfig>(getAI());
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    if (open) {
      setConfig(getAI());
      setTestResult(null);
    }
  }, [open]);

  const patch = (part: Partial<AIConfig>) => setConfig((prev) => ({ ...prev, ...part }));

  const save = () => {
    setAI(config);
    onSaved(config);
    onClose();
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    const prev = getAI();
    try {
      setAI(config);
      const res = await apiClient.testAI();
      setTestResult({ ok: res.ok, message: res.message });
    } catch (err: any) {
      setTestResult({ ok: false, message: err?.message || "连接失败" });
    } finally {
      setAI(prev);
      setTesting(false);
    }
  };

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    patch({
      base_url: preset.base_url,
      text_model: preset.text_model,
      image_model: preset.image_model,
      tts_model: preset.tts_model,
    });
    setTestResult(null);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="AI 接入设置"
      subtitle="平台不卖积分。你可以直接用演示模式，也可以填自己的密钥。"
      wide
    >
      <div className="seg">
        <button
          className={`seg-item ${config.mode === "demo" ? "active" : ""}`}
          onClick={() => patch({ mode: "demo" })}
        >
          <strong>演示模式</strong>
          <span>零成本，内置模板生成</span>
        </button>
        <button
          className={`seg-item ${config.mode === "byok" ? "active" : ""}`}
          onClick={() => patch({ mode: "byok" })}
        >
          <strong>自带密钥（BYOK）</strong>
          <span>用你自己的模型额度</span>
        </button>
      </div>

      <div className={`ai-form ${config.mode === "demo" ? "muted" : ""}`}>
        <div className="preset-row">
          <span>快速填充：</span>
          {PRESETS.map((p) => (
            <button key={p.name} className="chip clickable" onClick={() => applyPreset(p)}>
              {p.name}
            </button>
          ))}
        </div>

        <Field label="API Base URL" hint="需兼容 OpenAI 接口，例如 https://api.openai.com/v1">
          <input
            value={config.base_url}
            onChange={(e) => patch({ base_url: e.target.value })}
            placeholder="https://api.openai.com/v1"
            spellCheck={false}
          />
        </Field>

        <Field label="API Key" hint="只保存在当前浏览器 localStorage，不写入服务端数据库">
          <input
            type="password"
            value={config.api_key}
            onChange={(e) => patch({ api_key: e.target.value })}
            placeholder="sk-..."
            spellCheck={false}
            autoComplete="off"
          />
        </Field>

        <div className="grid two">
          <Field label="文本模型" hint="大纲 / 剧本 / 分镜">
            <input
              value={config.text_model}
              onChange={(e) => patch({ text_model: e.target.value })}
              placeholder="gpt-4o-mini"
              spellCheck={false}
            />
          </Field>
          <Field label="图像模型" hint="分镜画面 / 角色形象">
            <input
              value={config.image_model}
              onChange={(e) => patch({ image_model: e.target.value })}
              placeholder="gpt-image-1"
              spellCheck={false}
            />
          </Field>
          <Field label="语音模型" hint="镜头台词配音（可选）">
            <input
              value={config.tts_model}
              onChange={(e) => patch({ tts_model: e.target.value })}
              placeholder="gpt-4o-mini-tts"
              spellCheck={false}
            />
          </Field>
          <Field label="音色" hint="如 alloy / verse / 中文音色名">
            <input
              value={config.tts_voice}
              onChange={(e) => patch({ tts_voice: e.target.value })}
              placeholder="alloy"
              spellCheck={false}
            />
          </Field>
        </div>

        <p className="notice">
          演示模式不会产生任何调用费用；分镜画面会生成带提示词的占位示意图，台词可用浏览器朗读免费试听。
        </p>

        {testResult && (
          <div className={`test-result ${testResult.ok ? "ok" : "err"}`}>
            {testResult.ok ? "✓ " : "✕ "}
            {testResult.message}
          </div>
        )}
      </div>

      <div className="modal-actions">
        <button className="btn ghost" onClick={onClose}>
          取消
        </button>
        <button className="btn ghost" onClick={test} disabled={testing || config.mode === "demo"}>
          {testing ? <Spinner /> : null}
          测试连接
        </button>
        <button className="btn primary" onClick={save}>
          保存设置
        </button>
      </div>
    </Modal>
  );
}
