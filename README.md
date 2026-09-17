# ReviewForge

A local-first AI video editor specialized for YouTube product review videos.

You provide a script, a voice-over, product info, a master editing prompt, and your own
editing assets (lower thirds, transitions, product images/video). ReviewForge analyzes the
voice-over, plans what should be shown for every sentence, and assembles a timeline that a
deterministic renderer turns into a finished MP4.

The AI decides **what** should happen. A deterministic renderer decides **how** it is
rendered. The AI never touches a video frame.

```
SCRIPT + VOICE  →  CONTENT UNDERSTANDING  →  VISUAL PLAN  →  ASSET SEARCH
→ ASSET RANKING  →  TIMELINE JSON  →  RENDERER (Remotion)  →  FINAL MP4
```

## Why local-first

Everything except a single LLM planning call runs on your machine: transcription, media
processing, asset ranking, and rendering. Project media never leaves your computer.

## Stack

- **Frontend**: Next.js / React (`apps/web`), talks to the backend over `localhost` only
- **Backend/orchestration**: Python FastAPI (`apps/api`), runs locally
- **Rendering**: Remotion (`packages/renderer`), deterministic, never calls an LLM
- **Media processing**: FFmpeg (invoked locally as a subprocess)
- **Shared contract**: a versioned Timeline JSON schema (`packages/timeline-schema`)
- **Local storage**: SQLite for project/asset/job metadata; project files live on disk

See [`docs/architecture.md`](docs/architecture.md) for the full design and
[`docs/local-development.md`](docs/local-development.md) to run everything locally.

## Status

**Phase 0 and Phase 1 complete.** The foundation (repo layout, local API, local dashboard,
timeline schema, a working Remotion test render, FFmpeg detection) is in place, and voice +
script intelligence works end-to-end: local Whisper transcription, script sentence parsing,
deterministic script↔Whisper alignment, and timestamp validation, producing
`work/transcript.json` and `work/sentences.json`. LLM-based sentence understanding, visual
planning, and asset search/ranking are not implemented yet — see `docs/architecture.md` for
the phased roadmap.
