import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
function parseJson(text: string): Json | undefined {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return undefined;
  try { return JSON.parse(trimmed) as Json; } catch { return undefined; }
}
const symbols: Record<string, string> = {
  rightarrow: "→", leftarrow: "←", leftrightarrow: "↔", Rightarrow: "⇒", Leftarrow: "⇐", Leftrightarrow: "⇔",
  uparrow: "↑", downarrow: "↓", to: "→", times: "×", div: "÷", pm: "±", leq: "≤", geq: "≥", neq: "≠", approx: "≈", infty: "∞", checkmark: "✓",
};
export function readableSymbols(text: string): string {
  return text.replace(/\$\s*\\([A-Za-z]+)\s*\$|\\\(\s*\\([A-Za-z]+)\s*\\\)/g, (match, dollar: string, paren: string) => symbols[dollar || paren] ?? match);
}
// Transform text nodes only: fenced code and inline code retain exact syntax.
function symbolPlugin() {
  return (tree: { type: string; value?: string; children?: unknown[] }) => {
    function visit(node: typeof tree) {
      if (node.type === "text" && node.value) node.value = readableSymbols(node.value);
      node.children?.forEach(child => visit(child as typeof tree));
    }
    visit(tree);
  };
}
function Value({ value, depth = 0 }: { value: Json; depth?: number }) {
  if (depth > 8) return <code>{JSON.stringify(value)}</code>;
  if (typeof value === "string") {
    const nested = parseJson(value);
    return nested !== undefined ? <Value value={nested} depth={depth + 1} /> : <span className="json-text">{readableSymbols(value)}</span>;
  }
  if (value === null) return <span className="quiet">null</span>;
  if (typeof value !== "object") return <span>{String(value)}</span>;
  if (Array.isArray(value) && value.length && value.every(row => row !== null && typeof row === "object" && !Array.isArray(row))) {
    const rows = value as Record<string, Json>[];
    const keys = [...new Set(rows.flatMap(row => Object.keys(row)))];
    return <div className="json-table-scroll"><table><thead><tr>{keys.map(key => <th key={key}>{key}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{keys.map(key => <td key={key}>{key in row ? <Value value={row[key]} depth={depth + 1} /> : <span className="quiet">Not provided</span>}</td>)}</tr>)}</tbody></table></div>;
  }
  const entries = Object.entries(value);
  if (!entries.length) return <span className="quiet">{Array.isArray(value) ? "Empty list" : "Empty object"}</span>;
  return <div className="json-table-scroll"><table><thead><tr><th>{Array.isArray(value) ? "Item" : "Field"}</th><th>Value</th></tr></thead><tbody>{entries.map(([key, child]) => <tr key={key}><th scope="row">{Array.isArray(value) ? Number(key) + 1 : key}</th><td><Value value={child} depth={depth + 1} /></td></tr>)}</tbody></table></div>;
}
function JsonOutput({ value, source }: { value: Json; source: string }) {
  const [raw, setRaw] = useState(false);
  return <section className="json-output" aria-label="Structured response"><div className="json-toolbar"><strong>{raw ? "JSON" : "Structured response"}</strong><button type="button" className="secondary" aria-pressed={raw} onClick={() => setRaw(!raw)}>{raw ? "View table" : "View JSON"}</button></div>{raw ? <pre><code>{source}</code></pre> : <Value value={value} />}</section>;
}
export function ReadableOutput({ text }: { text: string }) {
  const value = parseJson(text);
  if (value !== undefined) return <JsonOutput value={value} source={text} />;
  return <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm, symbolPlugin]} components={{
    pre: ({ children, node }) => {
      const code = node?.children[0];
      if (code?.type === "element" && code.tagName === "code") {
        const source = code.children.map(child => child.type === "text" ? child.value : "").join("");
        const parsed = parseJson(source);
        if (parsed !== undefined) return <JsonOutput value={parsed} source={source} />;
      }
      return <pre>{children}</pre>;
    },
    a: ({ href, children }) => <a href={href} rel="noreferrer noopener" target="_blank">{children}</a>,
    img: ({ alt, src }) => <span className="quiet">{alt || "Image"}{src ? ` (${src})` : ""}</span>,
  }}>{text}</ReactMarkdown></div>;
}
