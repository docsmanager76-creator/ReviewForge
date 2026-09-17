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

export interface ProjectDetail extends ProjectSummary {
  scriptPath: string;
  voiceoverPath: string;
  masterPrompt: string;
  product: ProductInput;
  directories: {
    root: string;
    input: string;
    assets: string;
    work: string;
    output: string;
  };
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
