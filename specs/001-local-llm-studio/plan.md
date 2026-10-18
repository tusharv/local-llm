# Implementation Plan: Local LLM Studio

**Branch**: `001-local-llm-studio` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-local-llm-studio/spec.md`

## Summary

Build a localhost web app that chats, checks vision, and benchmarks any local LLM through an OpenAI-compatible `/v1` endpoint. Ollama is one saved preset with pull, delete, and native capability flags. Chats, images, and results stay in `./data`. After download, `python -m studio` runs an interactive terminal flow: it reports which local servers are available, prints install and start commands for the rest, then opens `http://127.0.0.1:8000`. macOS, Windows, and Linux use that same command. The README keeps the long per-OS guide.

## Technical Context

**Language/Version**: Python 3.11+ and TypeScript on Node 20+

**Primary Dependencies**: FastAPI, uvicorn, httpx, Vite, React

**Storage**: SQLite stdlib in `./data/studio.db`, image files in `./data/uploads/`

**Testing**: pytest with `tmp_path` and a mocked HTTP server. GitHub Actions on `ubuntu-latest`, `windows-latest`, and `macos-latest`

**Target Platform**: macOS, Windows, and Linux. The Studio process binds to `127.0.0.1`. The engine is a local or confirmed private-network OpenAI-compatible server

**Project Type**: Local web application (Python API plus a Vite frontend)

**Performance Goals**: Single-user streaming chat. Benchmarks run one model at a time. No concurrency target

**Constraints**: No telemetry, no public cloud engines, no install or launch of model runtimes, no macOS-only APIs, no bash-only run path. Onboarding may open the system browser to Studio only. Benchmark numbers are speed, not quality

**Scale/Scope**: One person, one first-run terminal flow, four pages (Setup, Chat, Models, Benchmarks), one versioned prompt suite, a bundled vision image

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Privacy: bind `127.0.0.1`, store data in `./data`, reject public cloud hosts, confirm private-network URLs. Pass.
- Engine contract: OpenAI-compatible client, Ollama extras behind kind `ollama`. Pass.
- Three operating systems: `pathlib`, one `python -m studio` onboarding command, npm scripts, CI matrix. Pass.
- Onboarding: detect and print commands, never execute runtime installers, open only Studio's own URL. Pass.
- Benchmarks: client-measured time to first token and tokens per second, labeled single-user. Pass.
- Tests: mocked HTTP, no model download. Pass.
- Scope: no judge model, RAG, voice, accounts, image generation, or concurrency suite. Pass.

No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-local-llm-studio/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http-api.md
├── spec.md
└── tasks.md
```

Project principles live in `.specify/memory/constitution.md`.

### Source Code (repository root)

```text
studio/
├── __init__.py
├── __main__.py
├── main.py
├── config.py
├── db.py
├── url_policy.py
├── onboarding/
│   ├── detect.py
│   ├── commands.py
│   └── flow.py
├── engines/
│   ├── openai_compatible.py
│   └── ollama.py
├── benchmarks/
│   ├── suite.py
│   └── runner.py
├── routes/
│   ├── health.py
│   ├── endpoints.py
│   ├── models.py
│   ├── chat.py
│   └── benchmarks.py
└── assets/
    └── vision-check.png

web/
├── index.html
├── package.json
└── src/
    ├── main.tsx
    ├── api.ts
    └── pages/
        ├── Setup.tsx
        ├── Chat.tsx
        ├── Models.tsx
        └── Benchmarks.tsx

tests/
├── unit/
└── integration/

.github/workflows/test.yml
pyproject.toml
README.md
```

**Structure Decision**: Web application layout with a Python package named `studio` and a `web/` Vite app. FastAPI serves `web/dist` after `npm run build`. Dev uses Vite's proxy to `127.0.0.1:8000`. `python -m studio` runs `studio/onboarding/flow.py` on first launch, then serves the app and opens the browser with the stdlib `webbrowser` module. No Makefile or shell script is required.

## Complexity Tracking

No constitution violations, so no extra projects or patterns are justified. SQLite is accessed from one module. There is no repository framework and no per-runtime native client beyond the Ollama preset.
