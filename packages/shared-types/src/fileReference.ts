/**
 * FileReference abstracts "how a file was chosen" away from "where the file lives" so the
 * pipeline (Python orchestration, timeline schema, Remotion renderer) never depends on how
 * the frontend obtained a path. Today only "local_path" is produced (a typed absolute path
 * in the local-first desktop UI). Later sources (native file picker, desktop wrapper /
 * Electron dialog, drag-and-drop) can be added without touching any downstream consumer,
 * because every FileReference is always resolved to an absolutePath by the API before it is
 * written into project state or the timeline JSON.
 */
export type FileReferenceSource = "local_path" | "native_picker" | "desktop_wrapper";

export interface FileReference {
  /** How this reference was produced. */
  source: FileReferenceSource;
  /** Absolute path on the local filesystem, resolved by the backend. Always present once stored. */
  absolutePath: string;
  /** Original value as provided by the UI, before resolution (e.g. a typed relative path). */
  originalValue?: string;
  /** Optional display name for UI purposes. */
  displayName?: string;
}
