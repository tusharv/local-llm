import { useId, type ReactNode } from "react";

const suggestions = [
  ["llama3.2:1b", "Llama 3.2 · 1B · Lightweight chat"],
  ["llama3.2:3b", "Llama 3.2 · 3B · Everyday chat"],
  ["qwen2.5-coder:3b", "Qwen 2.5 Coder · 3B · Code"],
  ["qwen2.5-coder:7b", "Qwen 2.5 Coder · 7B · Code"],
  ["gemma3:4b", "Gemma 3 · 4B · Text and images"],
];

export function ModelPicker({ value, onChange, action }: { value: string; onChange: (value: string) => void; action?: ReactNode }) {
  const id = useId();
  const custom = value !== "" && !suggestions.some(([name]) => name === value);
  return <div className="model-picker">
    <label htmlFor={id}>Model to download</label>
    <div className="model-download-controls"><select id={id} value={custom ? "custom" : value} onChange={event => onChange(event.target.value === "custom" ? " " : event.target.value)}>
      <option value="">Choose a model…</option>
      {suggestions.map(([name, label]) => <option key={name} value={name}>{label}</option>)}
      <option value="custom">Other model / custom tag…</option>
    </select>{action}</div>
    {custom ? <label>Custom model name<input value={value.trimStart()} onChange={event => onChange(event.target.value || " ")} placeholder="e.g. mistral:7b" /></label> : null}
    <small>Suggested downloads from the <a href="https://ollama.com/library" target="_blank" rel="noreferrer">Ollama library</a>. Larger models need more memory. Downloads require internet access.</small>
  </div>;
}
