# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this project is

ReviewForge is a **local-first** AI video editor for YouTube product review videos. See
`docs/architecture.md` for the full design and `docs/local-development.md` to run it.

## Non-negotiable architectural rules

1. **The renderer never calls an LLM.** `packages/renderer` (Remotion) consumes only a
   validated Timeline JSON. If you find yourself adding an API key, a network call, or any
   "smart" decision-making inside `packages/renderer`, stop — that logic belongs in
   `apps/api`, upstream of the Timeline JSON.
2. **Timeline JSON is the only contract** between the Python/AI half and the Remotion half.
   Do not add a second channel (e.g. having the renderer read from SQLite or call the API)
   between them.
3. **Local-first, minimal cloud dependency.** The only permitted network call in the pipeline
   is an LLM planning request (text in, structured JSON out). Never send audio/image/video
   bytes off the local machine. Do not introduce Docker, Redis, queues, or a hosted database
   — this is a single-user local tool.
4. **No secrets on disk.** `apps/api/reviewforge/config.py` reads the LLM API key only from
   the `REVIEWFORGE_LLM_API_KEY` environment variable. Never add a code path that writes an
   API key to `config.json` or anywhere else in the data directory.
5. **FileReference, not bare paths.** Frontend → backend file inputs go through the
   `FileReference` abstraction (`packages/shared-types/src/fileReference.ts`,
   `apps/api/reviewforge/models/file_reference.py`) so a future native file picker or desktop
   wrapper can be added without touching pipeline code. The normal Create Project flow uses
   the `browser_upload` source (`POST /projects/with-files`) — never assume the frontend can
   read or send an OS path; a browser can only ever hand over file *content*.
6. **Schema changes are versioned.** Any breaking change to
   `packages/timeline-schema/src/schema.ts` must bump `TIMELINE_SCHEMA_VERSION`'s major
   component and re-run `npm run export-schema`.

## Repo layout

```
apps/web        Next.js frontend (localhost:3000)
apps/api        Python FastAPI backend (localhost:8000) — orchestration, Whisper, SQLite
packages/timeline-schema   Versioned Zod schema, the Python/Remotion contract
packages/shared-types      Cross-package enums + FileReference
packages/renderer          Remotion project — deterministic rendering only
docs/                       Architecture + local dev docs
```

## Commands

- `npm install` (root) — installs web app + TS packages via npm workspaces
- `npm run export-schema` — regenerate JSON Schema from the Zod source of truth
- `cd apps/api && pytest` — backend test suite
- `cd apps/web && npm run dev` — frontend dev server
- `cd apps/api && uvicorn reviewforge.main:app --reload --port 8000` — backend dev server
- `cd packages/renderer && npm run render:sample` — render the sample Timeline JSON to MP4

## Current status

Phase 0 (foundation) and Phase 1 (voice + script intelligence) are complete:

- Phase 0: repo scaffolding, local API + dashboard, SQLite project/product/job tables,
  versioned timeline schema, a working Remotion test render, FFmpeg detection.
- Phase 1: local Whisper transcription (`apps/api/reviewforge/pipeline/whisper_backend.py`,
  faster-whisper), script sentence parsing (`script_parser.py`), deterministic script↔Whisper
  alignment (`alignment.py`, stdlib `difflib` — no LLM), timestamp validation
  (`validation.py`), `POST /projects/{id}/analyze/voice` + `GET /jobs/{id}` +
  `GET /projects/{id}/voice-analysis`, a CLI (`python -m reviewforge.pipeline.analyze_voice`),
  and an "Analyze Voice" dashboard control.

Also since Phase 1: a Settings UI (`/settings`, "Storage & Data") lets the user choose the
data directory location without touching a terminal (`GET/PUT /settings`,
`GET /settings/browse`, `POST /settings/browse-native`), backed by a pointer file at
`~/.reviewforge/settings.json` (env var `REVIEWFORGE_DATA_DIR` still wins over it — see
`config.py`'s `_resolve_data_dir`). The recommended/default location on Windows is
`F:\ReviewForge` (`config.py`'s `WINDOWS_DEFAULT_DATA_DIR`) — deliberately not
`D:\ReviewForgeData`, `F:\ReviewForgeData`, or a path under `C:\Users\...`; non-Windows
(dev/CI) keeps the `~/ReviewForgeData` home-relative default since a drive-letter default
makes no sense there. Create Project uploads files instead of requiring typed
paths (`POST /projects/with-files`); the original typed-path `POST /projects` still exists for
programmatic/CLI use and is what the test suite exercises.

No LLM-based sentence understanding, visual planning, or asset search/ranking is implemented
yet — sentences.json's content-understanding fields (contentType, topic, visualIntent,
preferredMediaType, fallbackMediaType, graphicsRequirement, transitionRequirement) are still
`null`, populated only in later phases. See the phased roadmap in `docs/architecture.md`
before adding one.
