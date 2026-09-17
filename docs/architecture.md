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
  source: "local_path" | "native_picker" | "desktop_wrapper";
  absolutePath: string;
  originalValue?: string;
  displayName?: string;
}
```

Phase 0 only produces `source: "local_path"` (a typed path resolved to an absolute path by
the API). A native file-picker dialog or a desktop wrapper (Electron, Tauri) can be added
later purely as new *sources* — every downstream consumer (project storage, timeline
builder, renderer) only ever sees a resolved `absolutePath` and does not care how it was
obtained.

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

0. **Scaffolding** (this phase) — repo layout, local API + UI, timeline schema, a working
   Remotion test render, FFmpeg detection.
1. **Content understanding** — Whisper integration, script-aligned sentence segmentation.
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
