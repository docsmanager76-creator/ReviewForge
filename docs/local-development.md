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
connected" pill and the project creation form.

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
| Whisper model | `REVIEWFORGE_WHISPER_MODEL` | `base` |
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
  projects/
    <project-id>/
      input/             # script, voiceover, product info as provided
      assets/
        images/
        video/
        graphics/
      work/              # transcript.json, sentences.json, visual_plan.json (later phases)
      output/
        timeline.json
        final.mp4
```
