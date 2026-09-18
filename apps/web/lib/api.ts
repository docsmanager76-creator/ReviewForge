/**
 * Thin client for the local FastAPI backend. Always targets localhost — this app has no
 * concept of a remote deployment. The base URL is only configurable so the API port can be
 * changed locally, never to point at a hosted backend.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface ProductInput {
  name: string;
  brand?: string;
  model?: string;
  url?: string;
  additionalUrls?: string[];
}

export interface CreateProjectInput {
  name: string;
  scriptPath: string;
  voiceoverPath: string;
  masterPrompt: string;
  product: ProductInput;
}

export interface ProjectSummary {
  id: string;
  name: string;
  createdAt: string;
  productName: string;
}

export interface ProjectDirectories {
  root: string;
  input: string;
  assets: string;
  work: string;
  output: string;
  reports: string;
}

export interface ProjectDetail extends ProjectSummary {
  scriptPath: string;
  voiceoverPath: string;
  masterPrompt: string;
  product: ProductInput;
  directories: ProjectDirectories;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${path} failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

/** For multipart/form-data submissions — the browser must set its own Content-Type (with the
 * multipart boundary), so this deliberately does not set headers the way request() does. */
async function requestFormData<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${path} failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

export function getHealth() {
  return request<{ status: string; version: string }>("/health");
}

export function listProjects() {
  return request<ProjectSummary[]>("/projects");
}

export function getProject(id: string) {
  return request<ProjectDetail>(`/projects/${id}`);
}

export function createProject(input: CreateProjectInput) {
  return request<ProjectDetail>("/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface CreateProjectWithFilesInput {
  name: string;
  productName: string;
  brand?: string;
  model?: string;
  productUrl?: string;
  masterPrompt?: string;
  scriptFile: File;
  voiceoverFile: File;
}

/** The normal Create Project workflow: the browser reads the selected files' bytes itself
 * (via <input type="file">) and uploads them — the user never types or needs to know a
 * filesystem path. See docs/local-development.md for why this is the only way a browser can
 * hand file content to a local backend without a native/desktop wrapper. */
export function createProjectWithFiles(input: CreateProjectWithFilesInput) {
  const formData = new FormData();
  formData.set("name", input.name);
  formData.set("productName", input.productName);
  if (input.brand) formData.set("brand", input.brand);
  if (input.model) formData.set("model", input.model);
  if (input.productUrl) formData.set("productUrl", input.productUrl);
  formData.set("masterPrompt", input.masterPrompt ?? "");
  formData.set("script", input.scriptFile);
  formData.set("voiceover", input.voiceoverFile);
  return requestFormData<ProjectDetail>("/projects/with-files", formData);
}

export interface AnalyzeVoiceResponse {
  jobId: string;
  status: string;
}

export interface JobStatus {
  id: string;
  projectId: string;
  type: string;
  status: "pending" | "running" | "succeeded" | "failed";
  stage: string | null;
  progress: number;
  error: string | null;
  result: Record<string, unknown> | null;
}

export interface VoiceAnalysisSummary {
  audioDuration: number;
  sentenceCount: number;
  needsReviewCount: number;
  transcriptStatus: string;
  alignmentStatus: string;
}

export function analyzeVoice(projectId: string) {
  return request<AnalyzeVoiceResponse>(`/projects/${projectId}/analyze/voice`, {
    method: "POST",
  });
}

export function getJob(jobId: string) {
  return request<JobStatus>(`/jobs/${jobId}`);
}

export function getVoiceAnalysis(projectId: string) {
  return request<VoiceAnalysisSummary>(`/projects/${projectId}/voice-analysis`);
}

export interface StorageStatus {
  exists: boolean;
  writable: boolean;
  freeBytes: number | null;
  totalBytes: number | null;
}

export interface SettingsInfo {
  dataDir: string;
  dataDirSource: "env" | "saved" | "default";
  projectsDir: string;
  modelsDir: string;
  status: StorageStatus;
}

export interface DirectoryEntry {
  name: string;
  path: string;
}

export interface DirectoryListing {
  path: string | null;
  parent: string | null;
  entries: DirectoryEntry[];
}

export interface NativeFolderPickerResult {
  available: boolean;
  path: string | null;
  message: string | null;
}

export function getSettings() {
  return request<SettingsInfo>("/settings");
}

export function updateDataDir(path: string) {
  return request<SettingsInfo>("/settings/data-dir", {
    method: "PUT",
    body: JSON.stringify({ path }),
  });
}

export function browseDirectory(path?: string) {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  return request<DirectoryListing>(`/settings/browse${query}`);
}

export function browseNative(initialPath?: string) {
  return request<NativeFolderPickerResult>("/settings/browse-native", {
    method: "POST",
    body: JSON.stringify({ initialPath: initialPath ?? null }),
  });
}
