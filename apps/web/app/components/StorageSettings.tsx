"use client";

import { useEffect, useState } from "react";
import { browseNative, getSettings, SettingsInfo, updateDataDir } from "../../lib/api";
import { FolderBrowserModal } from "./FolderBrowserModal";

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "unknown";
  const gb = bytes / 1024 ** 3;
  return `${gb.toFixed(1)} GB`;
}

const SOURCE_LABEL: Record<SettingsInfo["dataDirSource"], string> = {
  env: "environment variable override (REVIEWFORGE_DATA_DIR)",
  saved: "chosen in Settings",
  default: "default location",
};

export function StorageSettings() {
  const [settings, setSettings] = useState<SettingsInfo | null>(null);
  const [pathInput, setPathInput] = useState("");
  const [showBrowser, setShowBrowser] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  function refresh() {
    getSettings()
      .then((s) => {
        setSettings(s);
        setPathInput(s.dataDir);
      })
      .catch((err) => setMessage({ kind: "error", text: err instanceof Error ? err.message : "Failed to load settings." }));
  }

  useEffect(refresh, []);

  async function saveDataDir(path: string) {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateDataDir(path);
      setSettings(updated);
      setPathInput(updated.dataDir);
      if (updated.dataDirSource === "env") {
        setMessage({
          kind: "error",
          text: "Saved, but REVIEWFORGE_DATA_DIR is set in this environment and overrides it — unset that variable to use the folder you just chose.",
        });
      } else {
        setMessage({ kind: "success", text: "Data directory updated. Existing projects at the old location were not moved." });
      }
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Failed to update data directory." });
    } finally {
      setSaving(false);
    }
  }

  async function handleChooseFolder() {
    setMessage(null);
    try {
      const result = await browseNative(settings?.dataDir);
      if (result.available && result.path) {
        await saveDataDir(result.path);
        return;
      }
      if (result.available && !result.path) {
        return; // user cancelled the native dialog — nothing to do
      }
      // Native dialog unavailable on this OS/session — fall back to the in-app browser.
      setShowBrowser(true);
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Failed to open folder picker." });
    }
  }

  if (!settings) {
    return (
      <section className="panel">
        <h2>Storage &amp; Data</h2>
        {message && <div className={`message ${message.kind}`}>{message.text}</div>}
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>Storage &amp; Data</h2>

      <dl className="settings-grid">
        <div>
          <dt>Data directory</dt>
          <dd>{settings.dataDir}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{SOURCE_LABEL[settings.dataDirSource]}</dd>
        </div>
        <div>
          <dt>Projects directory</dt>
          <dd>{settings.projectsDir}</dd>
        </div>
        <div>
          <dt>Models directory</dt>
          <dd>{settings.modelsDir}</dd>
        </div>
        <div>
          <dt>Storage status</dt>
          <dd>
            {settings.status.exists ? "exists" : "will be created"},{" "}
            {settings.status.writable ? "writable" : "not writable"}
            {settings.status.freeBytes !== null && ` — ${formatBytes(settings.status.freeBytes)} free`}
          </dd>
        </div>
      </dl>

      <div className="field">
        <label htmlFor="dataDirInput">Change data directory</label>
        <div className="row-inline">
          <input
            id="dataDirInput"
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            placeholder="D:\ReviewForgeData"
          />
          <button className="secondary" onClick={handleChooseFolder} disabled={saving}>
            Choose Folder…
          </button>
          <button className="primary" onClick={() => saveDataDir(pathInput)} disabled={saving || !pathInput}>
            Save
          </button>
        </div>
        <p className="hint">
          "Choose Folder" opens a native Windows folder dialog when running on Windows with a
          desktop session; otherwise it falls back to an in-app folder browser. Typing a path
          directly always works too.
        </p>
      </div>

      {message && <div className={`message ${message.kind}`}>{message.text}</div>}

      {showBrowser && (
        <FolderBrowserModal
          initialPath={settings.dataDir}
          onClose={() => setShowBrowser(false)}
          onSelect={(path) => {
            setShowBrowser(false);
            saveDataDir(path);
          }}
        />
      )}
    </section>
  );
}
