import type { ReactNode } from "react";

function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.filter(Boolean).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return <span key={i}>{part}</span>;
  });
}

export function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let list: string[] = [];

  const flushList = () => {
    if (!list.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`}>
        {list.map((item, i) => (
          <li key={i}>{inline(item)}</li>
        ))}
      </ul>,
    );
    list = [];
  };

  lines.forEach((raw, i) => {
    const line = raw.trimEnd();
    if (line.startsWith("- ")) {
      list.push(line.slice(2));
      return;
    }
    flushList();
    if (!line.trim()) {
      return;
    }
    if (line === "---") {
      blocks.push(<hr key={i} />);
      return;
    }
    if (line.startsWith("### ")) {
      blocks.push(<h4 key={i}>{inline(line.slice(4))}</h4>);
      return;
    }
    if (line.startsWith("## ")) {
      blocks.push(<h3 key={i}>{inline(line.slice(3))}</h3>);
      return;
    }
    if (line.startsWith("# ")) {
      blocks.push(<h2 key={i}>{inline(line.slice(2))}</h2>);
      return;
    }
    if (line.startsWith("> ")) {
      blocks.push(<blockquote key={i}>{inline(line.slice(2))}</blockquote>);
      return;
    }
    blocks.push(<p key={i}>{inline(line)}</p>);
  });
  flushList();

  return <div className="md">{blocks}</div>;
}
