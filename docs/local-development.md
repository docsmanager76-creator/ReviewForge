# Local Development

ReviewForge is local-first: everything in this guide runs on your own machine
(instructions are OS-agnostic; paths shown as `C:\...` on Windows or `~/...` on macOS/Linux).

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- FFmpeg + FFprobe on your `PATH` (`ffmpeg -version` should work in a terminal)

## 1. Install dependencies

From the repo root (installs the web app and all TypeScript packages via npm workspaces):

```bash
npm install
```

Backend (Python), from `apps/api`:

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Export the Timeline JSON Schema (needed once, and after any schema change)

```bash
npm run export-schema
```

This writes `packages/timeline-schema/dist/*.schema.json`.

## 3. Run the backend

```bash
cd apps/api
uvicorn reviewforge.main:app --reload --port 8000
```

- Health check: `curl http://127.0.0.1:8000/health`
- On first run this creates `~/ReviewForgeData/` (override with the `REVIEWFORGE_DATA_DIR`
  env var) containing `app.db`, `config.json`, and `projects/`.

## 4. Run the frontend

```bash
cd apps/web
cp .env.local.example .env.local   # points NEXT_PUBLIC_API_BASE_URL at localhost:8000
npm run dev
```

Open http://127.0.0.1:3000 — you should see the ReviewForge dashboard with an "API
connected" pill and the Create Project form. Creating a project only ever needs you to click
"Select Script File" / "Select Voiceover File" — no path typing required. Visit
http://127.0.0.1:3000/settings ("Storage & Data") to see or change where ReviewForge stores
its data; "Choose Folder" opens a native Windows dialog when available, or an in-app folder
browser otherwise.

## 5. Run the Remotion test render

```bash
cd packages/renderer
npm run render:sample
```

Renders `sample/timeline.sample.json` to `packages/renderer/output/sample.mp4`
(1920x1080 H.264).

> In sandboxed environments where Remotion cannot download its managed Chromium (network
> egress restrictions), set `REVIEWFORGE_CHROME_HEADLESS_SHELL_PATH` to a local Chromium
> headless-shell binary before running the render — `remotion.config.ts` picks it up
> automatically. A normal Windows dev machine does not need this.

## 6. Run the backend test suite

```bash
cd apps/api
pytest
```

## 7. Voice + script analysis (Phase 1)

Install the optional Whisper dependency (not required for the API, the frontend, or the test
suite — only for running real transcription):

```bash
cd apps/api
pip install -r requirements-whisper.txt
```

Then, once a project exists (created via the dashboard or the API), either:

- **From the dashboard**: click "Analyze Voice" on the project's row and watch the progress
  label; when it finishes, voice duration, sentence count, and alignment status appear inline.
- **From the API**: `POST /projects/{project_id}/analyze/voice` returns a `jobId`; poll
  `GET /jobs/{jobId}` until `status` is `succeeded`/`failed`.
- **From the CLI** (fastest for debugging, no frontend needed):

  ```bash
  cd apps/api
  python -m reviewforge.pipeline.analyze_voice <project-id>
  ```

All three produce `work/transcript.json` (raw Whisper output) and `work/sentences.json`
(script sentences aligned to that audio, with `alignmentConfidence`/`needsReview` per
sentence). The Whisper model is cached under `~/ReviewForgeData/models/` and is not
re-downloaded on subsequent runs. Model size is configurable via `WHISPER_MODEL` (or
`REVIEWFORGE_WHISPER_MODEL`) — `tiny`, `base`, or `small`; defaults to `base`.

## 8. Choosing where ReviewForge stores its data

No PowerShell needed for this either: open **Settings → Storage & Data** in the dashboard.
It shows the current data/projects/models directories and storage status, and lets you change
the data directory two ways:

- **Choose Folder…** — tries a real native Windows folder dialog (works when running on
  Windows with an interactive desktop session); falls back automatically to an in-app folder
  browser everywhere else (e.g. this dev sandbox).
- **Type a path directly** into the field and click Save.

`REVIEWFORGE_DATA_DIR` still works exactly as before and always wins over whatever is saved
in Settings — useful for tests and CI, where you want a fully isolated, disposable location
regardless of what a developer's machine has configured.

An optional integration test exercises the real Whisper backend (skipped by default since it
needs the model download and `faster-whisper` installed):

```bash
REVIEWFORGE_RUN_WHISPER_INTEGRATION_TEST=1 pytest tests/test_whisper_integration.py
```

## Configuration

`apps/api/reviewforge/config.py` resolves settings in this order (highest wins):
environment variables → `~/ReviewForgeData/config.json` → built-in defaults.

| Setting | Env var | Default |
|---|---|---|
| Data directory | `REVIEWFORGE_DATA_DIR` | `~/ReviewForgeData` |
| FFmpeg path | `REVIEWFORGE_FFMPEG_PATH` | `ffmpeg` (from `PATH`) |
| FFprobe path | `REVIEWFORGE_FFPROBE_PATH` | `ffprobe` (from `PATH`) |
| Node path | `REVIEWFORGE_NODE_PATH` | `node` |
| Python path | `REVIEWFORGE_PYTHON_PATH` | `python` |
| Renderer dir | `REVIEWFORGE_RENDERER_DIR` | `packages/renderer` |
| Whisper model | `REVIEWFORGE_WHISPER_MODEL` (or bare `WHISPER_MODEL`) | `base` |
| Whisper device | `REVIEWFORGE_WHISPER_DEVICE` | `cpu` |
| LLM provider | `REVIEWFORGE_LLM_PROVIDER` | `anthropic` |
| LLM model | `REVIEWFORGE_LLM_MODEL` | `claude-sonnet-5` |
| **LLM API key** | `REVIEWFORGE_LLM_API_KEY` | *(required, never persisted to disk)* |

`config.json` never contains secrets — the LLM API key is read directly from the environment
on every access and is never written to `config.json`, logged, or included in any API
response.

## Project data layout

```
~/ReviewForgeData/
  app.db                # SQLite: project, product, job tables — metadata only
  config.json            # non-secret settings
  models/                # local Whisper model cache (faster-whisper download_root)
  projects/
    <project-id>/
      input/             # script, voiceover, product info as provided
      assets/
        images/
        video/
        graphics/
      work/              # transcript.json, sentences.json (visual_plan.json in a later phase)
      output/
        timeline.json
        final.mp4
```
