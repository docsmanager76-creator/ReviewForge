/**
 * FileReference abstracts "how a file was chosen" away from "where the file lives" so the
 * pipeline (Python orchestration, timeline schema, Remotion renderer) never depends on how
 * the frontend obtained a path. Sources produced so far: "local_path" (a typed absolute path)
 * and "browser_upload" (the browser read a file's bytes via <input type="file"> and the
 * backend wrote them into the project's input/ folder — this is how Create Project avoids
 * ever needing the user to type or know a Windows path). A future native file picker or
 * desktop wrapper (Electron dialog) can be added as another source without touching any
 * downstream consumer, because every FileReference is always resolved to an absolutePath by
 * the API before it is written into project state or the timeline JSON.
 */
export type FileReferenceSource = "local_path" | "browser_upload" | "native_picker" | "desktop_wrapper";

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
