import { useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { IconCheck, IconChevronDown, IconX } from "@tabler/icons-react";

export function ChatPicker({ label, value, options, disabled, allowCustom, onChange }: {
  label: string; value: string; options: { value: string; label: string }[];
  disabled?: boolean; allowCustom?: boolean; onChange: (value: string) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const titleId = useId();
  function close() { dialog.current?.close(); setOpen(false); trigger.current?.focus(); }
  function choose(next: string) { onChange(next); close(); }
  const filtered = options.filter(option => option.label.toLowerCase().includes(query.toLowerCase()));
  return <>
    <button ref={trigger} type="button" className="chat-picker-trigger" aria-label={`${label}: ${options.find(option => option.value === value)?.label || value || "Choose"}`} aria-haspopup="dialog" aria-expanded={open} disabled={disabled} onClick={() => { setQuery(""); setOpen(true); dialog.current?.showModal(); }}>
      <span>{options.find(option => option.value === value)?.label || value || `Choose ${label.toLowerCase()}`}</span><IconChevronDown size={14} />
    </button>
    {createPortal(<dialog ref={dialog} className="chat-picker-dialog" aria-labelledby={titleId} onCancel={() => { setOpen(false); }} onClick={event => { if (event.target === event.currentTarget) close(); }}>
      <div className="chat-picker-content">
        <header><div><h2 id={titleId}>Choose {label.toLowerCase()}</h2><p>{allowCustom ? "Select an installed model or enter its exact name." : "Choose where to send this conversation."}</p></div><button type="button" className="secondary" aria-label="Close picker" onClick={close}><IconX size={18} /></button></header>
        <label>Search {label.toLowerCase()}<input autoFocus type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={`Find ${label.toLowerCase()}…`} /></label>
        <div className="chat-picker-options">
          {filtered.map(option => <button type="button" key={option.value} aria-pressed={option.value === value} onClick={() => choose(option.value)}><span>{option.label}</span>{option.value === value ? <IconCheck size={18} /> : null}</button>)}
          {!filtered.length ? <p className="quiet">No matching {label.toLowerCase()} found.</p> : null}
        </div>
        {allowCustom && query.trim() && !options.some(option => option.value === query.trim()) ? <button type="button" className="custom-model-choice" onClick={() => choose(query.trim())}>Use “{query.trim()}”</button> : null}
      </div>
    </dialog>, document.body)}
  </>;
}
