"use client";

import { useEffect, useRef, useState } from "react";
import { analyzeVoice, getJob, getVoiceAnalysis, VoiceAnalysisSummary } from "../../lib/api";

type Phase = "idle" | "running" | "done" | "error";

const POLL_INTERVAL_MS = 1500;

export function VoiceAnalysisControls({ projectId }: { projectId: string }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<VoiceAnalysisSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getVoiceAnalysis(projectId)
      .then((s) => {
        if (!cancelled) {
          setSummary(s);
          setPhase("done");
        }
      })
      .catch(() => {
        // No analysis has run yet — leave phase as "idle".
      });
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [projectId]);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function handleClick() {
    setPhase("running");
    setError(null);
    setProgress(0);
    setStage("starting");
    try {
      const { jobId } = await analyzeVoice(projectId);
      pollRef.current = setInterval(async () => {
        try {
          const job = await getJob(jobId);
          setStage(job.stage);
          setProgress(job.progress);
          if (job.status === "succeeded") {
            stopPolling();
            const s = await getVoiceAnalysis(projectId);
            setSummary(s);
            setPhase("done");
          } else if (job.status === "failed") {
            stopPolling();
            setError(job.error ?? "Voice analysis failed.");
            setPhase("error");
          }
        } catch (err) {
          stopPolling();
          setError(err instanceof Error ? err.message : "Failed to check job status.");
          setPhase("error");
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start voice analysis.");
      setPhase("error");
    }
  }

  return (
    <div className="voice-analysis">
      <button className="secondary" onClick={handleClick} disabled={phase === "running"}>
        {phase === "running" ? `Analyzing… ${stage ?? ""} ${progress}%` : "Analyze Voice"}
      </button>
      {summary && (
        <dl className="voice-summary">
          <div>
            <dt>Voice duration</dt>
            <dd>{summary.audioDuration.toFixed(2)}s</dd>
          </div>
          <div>
            <dt>Transcript</dt>
            <dd>{summary.transcriptStatus}</dd>
          </div>
          <div>
            <dt>Sentences</dt>
            <dd>{summary.sentenceCount}</dd>
          </div>
          <div>
            <dt>Alignment</dt>
            <dd>{summary.alignmentStatus}</dd>
          </div>
          <div>
            <dt>Needs review</dt>
            <dd>{summary.needsReviewCount}</dd>
          </div>
        </dl>
      )}
      {error && <div className="message error">{error}</div>}
    </div>
  );
}
