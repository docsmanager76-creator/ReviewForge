"use client";

import { useRef, useState } from "react";
import { createProjectWithFiles } from "../../lib/api";

const emptyText = {
  name: "",
  productName: "",
  brand: "",
  productUrl: "",
  masterPrompt: "",
};

/**
 * The normal Create Project workflow: script and voiceover are picked with a native browser
 * file input and their bytes are uploaded to the local backend, which writes them into the
 * project's own input/ folder. No Windows path is ever typed or required.
 */
export function CreateProjectForm({ onCreated }: { onCreated: () => void }) {
  const [text, setText] = useState(emptyText);
  const [scriptFile, setScriptFile] = useState<File | null>(null);
  const [voiceoverFile, setVoiceoverFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const scriptInputRef = useRef<HTMLInputElement>(null);
  const voiceoverInputRef = useRef<HTMLInputElement>(null);

  function update<K extends keyof typeof emptyText>(key: K, value: string) {
    setText((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!scriptFile || !voiceoverFile) {
      setMessage({ kind: "error", text: "Select both a script file and a voiceover file." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      await createProjectWithFiles({
        name: text.name,
        productName: text.productName,
        brand: text.brand || undefined,
        productUrl: text.productUrl || undefined,
        masterPrompt: text.masterPrompt || undefined,
        scriptFile,
        voiceoverFile,
      });
      setMessage({ kind: "success", text: "Project created." });
      setText(emptyText);
      setScriptFile(null);
      setVoiceoverFile(null);
      if (scriptInputRef.current) scriptInputRef.current.value = "";
      if (voiceoverInputRef.current) voiceoverInputRef.current.value = "";
      onCreated();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Failed to create project." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <h2>Create Project</h2>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="name">Project Name</label>
          <input id="name" required value={text.name} onChange={(e) => update("name", e.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="productName">Product Name</label>
          <input
            id="productName"
            required
            value={text.productName}
            onChange={(e) => update("productName", e.target.value)}
          />
        </div>

        <div className="row">
          <div className="field">
            <label htmlFor="brand">Brand</label>
            <input id="brand" value={text.brand} onChange={(e) => update("brand", e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="productUrl">Product URL (optional)</label>
            <input
              id="productUrl"
              placeholder="https://..."
              value={text.productUrl}
              onChange={(e) => update("productUrl", e.target.value)}
            />
          </div>
        </div>

        <div className="row">
          <div className="field">
            <label htmlFor="scriptFile">Select Script File</label>
            <input
              id="scriptFile"
              ref={scriptInputRef}
              type="file"
              required
              accept=".md,.txt"
              onChange={(e) => setScriptFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="field">
            <label htmlFor="voiceoverFile">Select Voiceover File</label>
            <input
              id="voiceoverFile"
              ref={voiceoverInputRef}
              type="file"
              required
              accept="audio/*"
              onChange={(e) => setVoiceoverFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="masterPrompt">Master Prompt (optional)</label>
          <textarea
            id="masterPrompt"
            rows={4}
            value={text.masterPrompt}
            onChange={(e) => update("masterPrompt", e.target.value)}
          />
        </div>

        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create Project"}
        </button>
        {message && <div className={`message ${message.kind}`}>{message.text}</div>}
      </form>
    </section>
  );
}
