"use client";

import { useEffect, useState } from "react";
import { createProject, listProjects, ProjectSummary } from "../../lib/api";
import { VoiceAnalysisControls } from "./VoiceAnalysisControls";

const emptyForm = {
  name: "",
  scriptPath: "",
  voiceoverPath: "",
  productName: "",
  brand: "",
  model: "",
  productUrl: "",
  masterPrompt: "",
};

export function ProjectDashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  function refresh() {
    listProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }

  useEffect(refresh, []);

  function update<K extends keyof typeof emptyForm>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      await createProject({
        name: form.name,
        scriptPath: form.scriptPath,
        voiceoverPath: form.voiceoverPath,
        masterPrompt: form.masterPrompt,
        product: {
          name: form.productName,
          brand: form.brand || undefined,
          model: form.model || undefined,
          url: form.productUrl || undefined,
          additionalUrls: [],
        },
      });
      setMessage({ kind: "success", text: "Project created." });
      setForm(emptyForm);
      refresh();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Failed to create project." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <section className="panel">
        <h2>New project</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="name">Project name</label>
            <input id="name" required value={form.name} onChange={(e) => update("name", e.target.value)} />
          </div>
          <div className="row">
            <div className="field">
              <label htmlFor="scriptPath">Script path</label>
              <input
                id="scriptPath"
                required
                placeholder="C:\Users\you\Videos\review\script.md"
                value={form.scriptPath}
                onChange={(e) => update("scriptPath", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="voiceoverPath">Voiceover path</label>
              <input
                id="voiceoverPath"
                required
                placeholder="C:\Users\you\Videos\review\voiceover.wav"
                value={form.voiceoverPath}
                onChange={(e) => update("voiceoverPath", e.target.value)}
              />
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label htmlFor="productName">Product name</label>
              <input
                id="productName"
                required
                value={form.productName}
                onChange={(e) => update("productName", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="brand">Brand</label>
              <input id="brand" value={form.brand} onChange={(e) => update("brand", e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label htmlFor="model">Model</label>
              <input id="model" value={form.model} onChange={(e) => update("model", e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="productUrl">Product URL</label>
              <input
                id="productUrl"
                placeholder="https://..."
                value={form.productUrl}
                onChange={(e) => update("productUrl", e.target.value)}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="masterPrompt">Master editing prompt</label>
            <textarea
              id="masterPrompt"
              rows={4}
              required
              value={form.masterPrompt}
              onChange={(e) => update("masterPrompt", e.target.value)}
            />
          </div>
          <button className="primary" type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Project"}
          </button>
          {message && <div className={`message ${message.kind}`}>{message.text}</div>}
        </form>
      </section>

      <section className="panel">
        <h2>Projects</h2>
        {projects.length === 0 ? (
          <p style={{ color: "var(--text-dim)", fontSize: 14 }}>No projects yet.</p>
        ) : (
          <ul className="project-list">
            {projects.map((p) => (
              <li key={p.id} className="project-item">
                <div className="project-item-header">
                  <span>
                    {p.name} <span className="id">— {p.productName}</span>
                  </span>
                  <span className="id">{p.id}</span>
                </div>
                <VoiceAnalysisControls projectId={p.id} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
