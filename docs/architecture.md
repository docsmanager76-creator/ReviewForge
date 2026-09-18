# ReviewForge Architecture

## Principles

1. **Local-first.** All media (voice-over, images, video clips, rendered output) stays on
   disk on the user's machine. The only network call in the entire pipeline is a single LLM
   request per planning step, and it sends text only (sentences, product name/URL, master
   prompt) — never audio, image, or video bytes.
2. **AI plans, renderer executes.** The Python backend and its LLM calls decide *what* should
   happen (which sentence gets which shot type, which lower-third, which transition). The
   Remotion renderer only *executes* that plan. The renderer must never call an LLM and must
   never make a creative decision — every rendering-relevant field it needs is already present
   in the Timeline JSON.
3. **Timeline JSON is the hard boundary.** It is the only artifact that crosses from the
   Python/AI half of the system to the Remotion/rendering half. It is schema-validated on
   both sides (Zod in TypeScript, the exported JSON Schema in Python).
4. **Simple over clever.** No Docker, no Redis, no queues, no microservices, no auth. This is
   a single-user local tool; a synchronous FastAPI call or a simple background task is enough.

## Data flow

```
SCRIPT + VOICE + PRODUCT INFO (local files, typed paths / FileReference)
        │
        ▼
CONTENT UNDERSTANDING   Whisper (local) + script-aligned sentence segmentation
        │
        ▼
VISUAL PLAN             LLM call (only network step) → per-sentence VisualIntent
        │
        ▼
ASSET SEARCH            local assets/ folder (+ later: stock/web search)
        │
        ▼
ASSET RANKING           deterministic relevance scoring + reuse-penalty memory (local)
        │
        ▼
TIMELINE JSON           schema-validated, written to disk
        │
        ▼
RENDERER (Remotion)     reads Timeline JSON + local files only, renders deterministically
        │
        ▼
FINAL MP4 (1920x1080)
```

## FileReference abstraction

The frontend never hands the pipeline a bare string path. It hands a `FileReference`
(`packages/shared-types/src/fileReference.ts`, mirrored in
`apps/api/reviewforge/models/file_reference.py`):

```ts
interface FileReference {
  source: "local_path" | "browser_upload" | "native_picker" | "desktop_wrapper";
  absolutePath: string;
  originalValue?: string;
  displayName?: string;
}
```

Phase 0 produced only `source: "local_path"` (a typed path resolved to an absolute path by
the API). The normal Create Project workflow now uses `source: "browser_upload"`: the browser
reads a selected file's bytes via `<input type="file">` (the only thing a website is ever
allowed to get from a file picker — never an OS path) and uploads them to
`POST /projects/with-files`, which writes them into that project's own `input/` folder. A
native file-picker dialog or a desktop wrapper (Electron, Tauri) can be added later purely as
another *source* — every downstream consumer (project storage, timeline builder, renderer)
only ever sees a resolved `absolutePath` and does not care how it was obtained.

## Choosing the data directory (Settings UI)

`config.json` normally lives *inside* the data directory — but if the data directory's own
location is user-chosen, something outside it must remember that choice. A small pointer file
at `~/.reviewforge/settings.json` (written by `PUT /settings/data-dir`) does exactly that and
nothing else. Precedence, highest wins: `REVIEWFORGE_DATA_DIR` env var (dev override) → the
saved pointer (the normal UI path, via Settings → "Storage & Data") → the built-in default —
**`F:\ReviewForge` on Windows** (`config.py`'s `WINDOWS_DEFAULT_DATA_DIR`; deliberately not
`D:\ReviewForgeData`, `F:\ReviewForgeData`, or anywhere under `C:\Users\...`), or
`~/ReviewForgeData` on non-Windows dev/CI machines, where a drive-letter default doesn't
apply. Changing the folder in the UI does not migrate existing projects — it starts fresh at
the new location.

"Choose Folder" tries a real native Windows folder dialog first (the backend shells out to
PowerShell's `FolderBrowserDialog` — this only works because the backend and browser run on
the same physical machine, which is the whole point of local-first) and falls back to an
in-app, backend-driven directory browser (`GET /settings/browse`) when that's unavailable
(non-Windows, no interactive desktop session, no PowerShell). Browser JavaScript itself never
gets filesystem access — see `apps/api/reviewforge/util/folder_picker.py` for the full
reasoning.

## Communication

- Next.js (`localhost:3000`) talks to FastAPI (`localhost:8000`) over plain `fetch`/JSON.
  CORS on the API is locked to `localhost:3000` / `127.0.0.1:3000`.
- Long-running work (transcription, LLM planning, rendering) is modeled as a `job` row in
  SQLite with a status the UI can poll — no websockets or queue system in Phase 0.
- FastAPI launches Remotion as a local subprocess (`npx remotion render ...`), passing the
  validated `timeline.json` as the render's input props. Output goes straight to the
  project's `output/` folder. There is no HTTP boundary between Python and Remotion.
- FastAPI shells out to `ffmpeg`/`ffprobe` for media probing/processing; paths are
  configurable, defaulting to whatever is on `PATH`.
- Whisper runs in-process inside the FastAPI backend so audio never has to leave the machine.

## Data models (Phase 0 subset — see `packages/timeline-schema/src/schema.ts`)

- **Product** — `name`, `brand`, `model`, `url`, `additionalUrls` — first-class from the
  start, even though web asset downloading is not implemented yet.
- **Project** — `id`, `title`, `product`, `createdAt`.
- **Sentence** — text, timing, `contentType`, `topic`, `visualIntent`, preferred/fallback
  media type, optional graphics/transition requirements. (Modeled in the schema now; the
  pipeline that produces Sentences is a later phase.)
- **VisualIntent** — `shotType` (hero / close_up / side_profile / action_demo / feature_shot /
  specification_shot / accessory_shot / lifestyle_context), a free-text `description`, and an
  optional `motionPreset`.
- **Asset** — id, product, type (image/video), source (local/stock/web_search), filePath,
  description, tags, `visualCategory` (shares the ShotType enum), quality score, and
  `usageHistory` for reuse-penalty tracking.
- **GraphicsRequirement / TransitionRequirement** — always a `template` name plus a `fields`
  map. Graphics are template-based; nothing is freely invented at render time.
- **Scene / Timeline** — see below.

## Timeline JSON schema (v1.0)

Source of truth: `packages/timeline-schema/src/schema.ts` (Zod). Exported to JSON Schema via
`npm run export-schema`, written to `packages/timeline-schema/dist/*.schema.json`, versioned
by `TIMELINE_SCHEMA_VERSION`. A major version bump means a breaking field change; both the
timeline builder (Python) and the renderer (Remotion) check this value.

```ts
{
  version: "1.0",
  project: { id, title, product, fps, resolution: { width: 1920, height: 1080 } },
  audio: { voiceoverPath, musicPath? },
  scenes: [
    {
      id, sentenceId, startTime, endTime,
      visual: { type: "image" | "video_clip", assetId, filePath, motionPreset?, trimStart?, trimEnd? },
      graphics: [{ template, fields, startTime, endTime }],
      transitionOut?: { template, duration }
    }
  ],
  globalGraphics: { productIntro?: { template, fields, startTime, endTime } }
}
```

This is the only artifact `packages/renderer` consumes. It is fully self-describing — file
paths, timings, template names, field values — so the renderer only interpolates/composes,
never decides.

## MVP (not yet implemented beyond Phase 0)

Script + voice-over + local images/videos + one CTA lower-third + one shape transition →
sentence analysis → visual matching → Timeline JSON → Remotion render → working MP4.

## Phased roadmap

0. **Scaffolding** (done) — repo layout, local API + UI, timeline schema, a working Remotion
   test render, FFmpeg detection.
1. **Content understanding — voice + script intelligence** (done) — local Whisper
   transcription, script sentence parsing, deterministic script↔Whisper alignment
   (`apps/api/reviewforge/pipeline/`), timestamp validation, `work/transcript.json` +
   `work/sentences.json`. Sentence-level LLM understanding (contentType, topic, visualIntent,
   etc.) is deliberately deferred to Phase 2 — Phase 1 leaves those fields `null`.
2. **Visual planning** — LLM call producing `VisualIntent` per sentence (structured JSON
   output only).
3. **Local asset pipeline** — asset ingestion, metadata tagging, naive relevance ranking,
   reuse-penalty memory.
4. **Timeline + MVP render** — timeline builder, one motion preset, one CTA lower-third, one
   shape transition, full MVP path on a real script.
5. **Graphics & motion library** — all motion presets, all lower-third templates, product
   intro graphics, CTA phrase detection.
6. **Asset intelligence** — stock/web asset search, section-level visual coverage reasoning.
7. **Quality control layer** — automated detection of repetition, bad timing, missing
   visuals/graphics.
8. **Human override UI** — scene-level asset replacement without a full rebuild.

## Risks / decisions carried from design review

- Align Whisper output to the provided script text rather than trusting raw ASR transcription.
- All LLM planner output must be schema-validated with retry-on-invalid-JSON; free-form text
  never reaches the renderer.
- No queue/Redis: pipeline runs are single-project, single-user, sequential.
- SQLite holds only metadata/state; media is always a file on disk, referenced by path.
