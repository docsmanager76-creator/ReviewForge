"use client";

import { useEffect, useState } from "react";
import { browseDirectory, DirectoryEntry } from "../../lib/api";

/**
 * Backend-driven folder browser: used whenever a native OS "Browse for Folder" dialog isn't
 * available (non-Windows, no interactive desktop session, PowerShell missing). The backend
 * lists real directories on the local machine (it has ordinary filesystem access — it's not
 * a remote server), and this modal just renders that as a click-through list. It is NOT a
 * native Explorer window; see docs/architecture.md for why a browser can't produce one.
 */
export function FolderBrowserModal({
  initialPath,
  onSelect,
  onClose,
}: {
  initialPath: string;
  onSelect: (path: string) => void;
  onClose: () => void;
}) {
  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const [parent, setParent] = useState<string | null>(null);
  const [entries, setEntries] = useState<DirectoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function load(path?: string) {
    setLoading(true);
    setError(null);
    browseDirectory(path)
      .then((listing) => {
        setCurrentPath(listing.path);
        setParent(listing.parent);
        setEntries(listing.entries);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to list folder."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(initialPath || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Choose a folder</h3>
        <p className="modal-path">{currentPath ?? "Drives"}</p>

        {loading && <p className="message">Loading…</p>}
        {error && <div className="message error">{error}</div>}

        {!loading && !error && (
          <ul className="folder-list">
            {parent && (
              <li>
                <button className="folder-entry" onClick={() => load(parent)}>
                  .. (up)
                </button>
              </li>
            )}
            {entries.length === 0 && !parent && (
              <li className="message">No subfolders here.</li>
            )}
            {entries.map((entry) => (
              <li key={entry.path}>
                <button className="folder-entry" onClick={() => load(entry.path)}>
                  {entry.name}
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="modal-actions">
          <button className="secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={!currentPath}
            onClick={() => currentPath && onSelect(currentPath)}
          >
            Select this folder
          </button>
        </div>
      </div>
    </div>
  );
}
