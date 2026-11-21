import { useCallback, useEffect, useState } from "react";
import { getAI } from "./api";
import { AISettings } from "./components/AISettings";
import { Projects } from "./pages/Projects";
import { Workspace } from "./pages/Workspace";
import type { AIConfig } from "./types";
import { AppCtx, type ToastKind } from "./ui";

function readRoute(): { pid: string | null } {
  const hash = window.location.hash.replace(/^#\/?/, "");
  if (hash.startsWith("p/")) return { pid: hash.slice(2) };
  return { pid: null };
}

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [ai, setAi] = useState<AIConfig>(getAI);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; kind: ToastKind } | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const notify = useCallback((message: string, kind: ToastKind = "ok") => {
    setToast({ message, kind });
  }, []);

  const openSettings = useCallback(() => setSettingsOpen(true), []);

  const openProject = (pid: string) => {
    window.location.hash = `#/p/${pid}`;
  };

  const backToList = () => {
    window.location.hash = "#/";
  };

  const demo = ai.mode === "demo";

  return (
    <AppCtx.Provider value={{ notify, openSettings }}>
      <div className="app">
        <header className="app-header">
          <button className="brand" onClick={backToList}>
            <span className="brand-mark">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M3.5 8.5h17v11.5h-17z" stroke="currentColor" strokeWidth="1.6" />
                <path d="M3.5 8.5 5.6 3h13.8l1.1 5.5" stroke="currentColor" strokeWidth="1.6" />
                <path d="m7 3.4 1.8 5m4.2-5 1.2 5m4.2-5 1.2 5" stroke="currentColor" strokeWidth="1.4" />
                <path d="M8.5 13.5h7M8.5 16.5h4.5" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            </span>
            <span className="brand-text">
              <strong>剧作工坊</strong>
              <em>ShortPlay Studio</em>
            </span>
          </button>

          <div className="header-right">
            <button className={`ai-chip ${demo ? "demo" : "byok"}`} onClick={openSettings}>
              <span className="ai-dot" />
              {demo ? "零积分 · 演示模式" : `BYOK · ${ai.text_model || "已接入"}`}
            </button>
            <button className="btn ghost sm hide-mobile" onClick={openSettings}>
              AI 接入设置
            </button>
          </div>
        </header>

        <main>
          {route.pid ? (
            <Workspace pid={route.pid} onBack={backToList} aiMode={ai.mode} />
          ) : (
            <Projects onOpen={openProject} />
          )}
        </main>

        <footer className="app-footer">
          <span>剧作工坊 · 本地半自动短剧创作台</span>
          <span className="muted">项目数据保存在本机 SQLite；密钥只留在你的浏览器</span>
        </footer>

        <AISettings
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          onSaved={(config) => {
            setAi(config);
            notify(config.mode === "demo" ? "已切换到零成本演示模式" : "已保存自己的 AI 接入配置", "ok");
          }}
        />

        {toast && <div className={`toast ${toast.kind}`}>{toast.message}</div>}
      </div>
    </AppCtx.Provider>
  );
}
