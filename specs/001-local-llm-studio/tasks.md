---
description: "Task list for Local LLM Studio"
---

# Tasks: Local LLM Studio

**Input**: Design documents from `/specs/001-local-llm-studio/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: Required by FR-015. Write the listed tests first and confirm they fail before the implementation they cover.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 through US6)
- File paths are in the descriptions

## Path Conventions

- Python package: `studio/`
- Frontend: `web/src/`
- Tests: `tests/unit/`, `tests/integration/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create the directory layout in `studio/`, `web/src/pages/`, `tests/unit/`, and `tests/integration/` per `specs/001-local-llm-studio/plan.md`
- [x] T002 Add `pyproject.toml` with FastAPI, uvicorn, httpx, and a pytest dev extra, plus `studio/__init__.py` and `studio/__main__.py` that call the app on `127.0.0.1:8000`
- [x] T003 [P] Add `web/package.json`, Vite, React, and TypeScript with a dev proxy to `http://127.0.0.1:8000`
- [x] T004 [P] Add `.gitignore` for `data/`, `web/node_modules/`, `web/dist/`, and Python caches
- [x] T005 [P] Add `LICENSE` as MIT

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage, URL policy, and the engine client that every story uses

**Critical**: No user story work begins until this phase is complete

- [x] T006 Implement `studio/config.py` with `pathlib` data dir `./data`, bind host `127.0.0.1`, and port `8000`
- [x] T007 Implement `studio/db.py` creating Endpoint, Conversation, Message, ModelFlag, BenchmarkRun, and BenchmarkResult from `specs/001-local-llm-studio/data-model.md`
- [x] T008 [P] Implement `studio/url_policy.py` to normalize a `/v1` base URL, allow loopback, require confirm for private-network hosts, and reject public cloud hosts
- [x] T009 [P] Add failing tests in `tests/unit/test_url_policy.py` for loopback accept, private-network confirm, and `https://api.openai.com/v1` reject
- [x] T010 Implement `studio/engines/openai_compatible.py` with health, list models, and streaming chat completions, including image data URLs and optional usage chunks
- [x] T011 Implement `studio/main.py` app factory, router mount, and startup creation of `./data` and `./data/uploads`
- [x] T012 Make `tests/unit/test_url_policy.py` pass

**Checkpoint**: Database and URL rules work without a live model server

---

## Phase 3: User Story 6 - First-run terminal onboarding (Priority: P1)

**Goal**: After download, `python -m studio` shows what is available, prints commands for the rest, and opens the local web UI

**Independent Test**: Scripted stdin and fake probes for macOS, Windows, and Linux print the right commands, never execute them, save a chosen running endpoint, write `data/onboarding.json`, and request a browser open at `http://127.0.0.1:8000`. A second run skips the questions. A non-tty stdin does not block or open a browser

### Tests for User Story 6

- [x] T046 [P] [US6] Add failing tests in `tests/unit/test_onboarding_commands.py` that macOS, Windows, and Linux each get their own Ollama, LM Studio, and llama.cpp install and start text
- [x] T047 [P] [US6] Add failing tests in `tests/unit/test_onboarding_flow.py` for running versus stopped versus missing, scripted endpoint choice, no subprocess launch, completion file, browser open, second-run skip, and non-tty skip

### Implementation for User Story 6

- [x] T048 [US6] Implement PATH and loopback port detection in `studio/onboarding/detect.py` for Ollama `11434`, LM Studio `1234`, and llama.cpp `8080`
- [x] T049 [US6] Implement per-OS command text in `studio/onboarding/commands.py` with no function that runs those commands
- [x] T050 [US6] Implement the `input()` menu in `studio/onboarding/flow.py`, including re-probe, skip, and writing `data/onboarding.json` from `specs/001-local-llm-studio/data-model.md`
- [x] T051 [US6] Wire `studio/__main__.py` so the first interactive run calls the flow, then serves `127.0.0.1:8000`, then opens that URL with `webbrowser` unless `--no-browser` is set. Honor `--onboard` and `--skip-onboard`. If stdin is not a terminal, serve without prompts and without a browser
- [x] T052 [US6] Make T046 and T047 pass

**Checkpoint**: A terminal first run reports local runtimes, prints copy-paste commands, and opens Studio. It does not install or start those runtimes

---

## Phase 4: User Story 1 - Private chat with a local model (Priority: P1)

**Goal**: Save an endpoint, see that it is up, stream a chat, and reload the transcript from `./data`

**Independent Test**: Against a mocked `/v1` server, save a loopback endpoint, stream one reply, restart the app pointer against the same temp database, and read the same messages

### Tests for User Story 1

- [x] T013 [P] [US1] Add failing stream-parse tests in `tests/unit/test_openai_stream.py` for time to first token and completion usage
- [x] T014 [P] [US1] Add failing chat persistence tests in `tests/integration/test_chat_api.py` for save, reload, cloud URL reject, and delete

### Implementation for User Story 1

- [x] T015 [US1] Implement endpoint create, list, and delete in `studio/routes/endpoints.py` per `specs/001-local-llm-studio/contracts/http-api.md`
- [x] T016 [US1] Implement `GET /api/health` in `studio/routes/health.py`
- [x] T017 [US1] Implement conversation create, list, get, and delete in `studio/routes/chat.py`
- [x] T018 [US1] Implement `POST /api/chat` SSE in `studio/routes/chat.py`, storing user and assistant messages
- [x] T019 [US1] Add `web/src/api.ts` plus `web/src/pages/Chat.tsx` and a minimal endpoint picker that can create the first endpoint
- [x] T020 [US1] Make T013 and T014 pass

**Checkpoint**: User Story 1 works on its own. A person can chat with a mocked or live local `/v1` server and refresh without losing the transcript

---

## Phase 5: User Story 2 - See and manage installed models (Priority: P2)

**Goal**: List models, show an effective vision flag, and pull or delete only on Ollama

**Independent Test**: A generic endpoint lists models and returns 400 on pull. An Ollama endpoint parses capabilities and streams pull progress from a mock

### Tests for User Story 2

- [x] T021 [P] [US2] Add failing tests in `tests/unit/test_ollama_capabilities.py` for vision capabilities, family-name fallback, and missing capabilities
- [x] T022 [P] [US2] Add failing tests in `tests/integration/test_models_api.py` that pull and delete return 400 for kind `openai`

### Implementation for User Story 2

- [x] T023 [US2] Implement `studio/engines/ollama.py` for `/api/show`, streamed `/api/pull`, and `/api/delete`
- [x] T024 [US2] Implement `GET /api/models`, `PUT /api/models/flags`, pull SSE, and delete in `studio/routes/models.py`
- [x] T025 [US2] Add `web/src/pages/Models.tsx` with the list, vision override, and Ollama-only pull and delete
- [x] T026 [US2] Make T021 and T022 pass

**Checkpoint**: Model list and Ollama management work without the vision-check or benchmark pages

---

## Phase 6: User Story 3 - Check vision (Priority: P2)

**Goal**: Attach an image in chat for a vision model, run the bundled vision check, and delete image files with the conversation

**Independent Test**: A vision model receives a data URL. A text model cannot be sent an image. Deleting the conversation removes the file under the temp data dir

### Tests for User Story 3

- [x] T027 [P] [US3] Add failing tests in `tests/integration/test_vision.py` for image store, text-model rejection, probe cache, and file cleanup on delete

### Implementation for User Story 3

- [x] T028 [US3] Add the bundled shapes image at `studio/assets/vision-check.png` and a fixed question constant next to it
- [x] T029 [US3] Extend `POST /api/chat` to accept an image only when the effective vision flag is true, and serve files from `./data/uploads` without path escape
- [x] T030 [US3] Implement `POST /api/vision-check` in `studio/routes/models.py` and update ModelFlag.probe_result
- [x] T031 [US3] Add image attach and the vision-check action in `web/src/pages/Chat.tsx` and `web/src/pages/Models.tsx`
- [x] T032 [US3] Make T027 pass

**Checkpoint**: Image chat and the vision check work against a mock, and cleanup is covered

---

## Phase 7: User Story 4 - Benchmark models on this machine (Priority: P2)

**Goal**: Run the versioned suite one model at a time, store speed rows, compare them, and export JSON

**Independent Test**: A mocked stream with a delayed first chunk produces the expected `ttft_ms` and tokens per second. A second start while `running` returns 409

### Tests for User Story 4

- [x] T033 [P] [US4] Add failing tests in `tests/unit/test_benchmark_math.py` for time to first token, usage-based tokens per second, and chunk-count fallback
- [x] T034 [P] [US4] Add failing tests in `tests/integration/test_benchmarks_api.py` for a full run, 409 while running, comparison payload, and JSON export

### Implementation for User Story 4

- [x] T035 [US4] Implement the text and vision cases and `suite_version` in `studio/benchmarks/suite.py`
- [x] T036 [US4] Implement the sequential runner, optional warmup, and repeat count in `studio/benchmarks/runner.py`
- [x] T037 [US4] Implement start, list, get, and export in `studio/routes/benchmarks.py` per the contract
- [x] T038 [US4] Add `web/src/pages/Benchmarks.tsx` with run progress, history, same-suite comparison, export, and the single-user speed explanation
- [x] T039 [US4] Make T033 and T034 pass

**Checkpoint**: Benchmark history is useful even if the setup guide is still a stub

---

## Phase 8: User Story 5 - Set up Studio on macOS, Windows, or Linux (Priority: P3)

**Goal**: A new person can install a runtime on their OS and connect it, from the README and the Setup page

**Independent Test**: README headings exist for macOS, Windows, and Linux under Ollama, LM Studio, and llama.cpp. The Setup page shows a down endpoint and a healthy one using `127.0.0.1`

### Implementation for User Story 5

- [x] T040 [US5] Add `web/src/pages/Setup.tsx` for endpoint create, health, model count, Ollama pull when kind is `ollama`, and the localhost-versus-`127.0.0.1` hint
- [x] T041 [US5] Serve `web/dist` from `studio/main.py` when that directory exists
- [x] T042 [US5] Write `README.md` with the same Studio install on all three operating systems, per-OS install steps for Ollama, LM Studio, and llama.cpp, RAM examples, troubleshooting, and the privacy rules from `.specify/memory/constitution.md`

**Checkpoint**: The quickstart in `specs/001-local-llm-studio/quickstart.md` can be followed from the README

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: CI and a full local test run

- [x] T043 [P] Add `.github/workflows/test.yml` running `pytest` on `ubuntu-latest`, `windows-latest`, and `macos-latest`
- [x] T044 Run `pytest` locally and fix failures in the tests or studio code they cover
- [x] T045 Walk `specs/001-local-llm-studio/quickstart.md` on this Mac against Ollama if the daemon can be started, and record any doc mismatch in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories
- **User Story 6 (Phase 3)**: Depends on Foundational. This is the first-run shell around the server. The page it opens becomes useful as later stories add UI
- **User Story 1 (Phase 4)**: Depends on Foundational. No dependency on later stories. Can be built beside US6
- **User Story 2 (Phase 5)**: Depends on Foundational. Uses the endpoint rows from US1 when the UI is wired, and the model API can be tested without the chat page
- **User Story 3 (Phase 6)**: Depends on US1 chat storage and US2 vision flags
- **User Story 4 (Phase 7)**: Depends on Foundational and US2 vision flags for the vision case. Text cases can be tested with a flag row inserted directly
- **User Story 5 (Phase 8)**: Depends on US1 health and US2 model list so Setup has something to show
- **Polish (Phase 9)**: Depends on the stories included in the run

### User Story Dependencies

- **US6 (P1)**: First runnable experience after Foundational. Onboarding plus a listening server
- **US1 (P1)**: Chat MVP. Can follow or sit beside US6
- **US2 (P2)**: After Foundational. Independently testable through the models API
- **US3 (P2)**: After US1 and US2
- **US4 (P2)**: After the engine client exists. Vision case after US2 flags
- **US5 (P3)**: After US1 and US2

### Parallel Opportunities

- T003, T004, and T005 can run in parallel after T001
- T008 and T009 can run in parallel with T006 and T007
- T046 and T047 can run in parallel
- T013 and T014 can run in parallel
- T021 and T022 can run in parallel
- T033 and T034 can run in parallel
- US2 model API work and US4 benchmark math can proceed in parallel once Foundational and the vision-flag row exist

---

## Parallel Example: User Story 1

```text
Task: "Add failing stream-parse tests in tests/unit/test_openai_stream.py"
Task: "Add failing chat persistence tests in tests/integration/test_chat_api.py"
```

---

## Implementation Strategy

### MVP First (User Story 6 and User Story 1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 6, so `python -m studio` onboards and opens the web UI
4. Complete Phase 4: User Story 1
5. Stop and validate a streamed chat against a local `/v1` server or the mock

### Incremental Delivery

1. Setup plus Foundational
2. US6 terminal onboarding and browser open
3. US1 chat (MVP)
4. US2 model list and Ollama pull/delete
5. US3 vision
6. US4 benchmarks
7. US5 three-OS guide and Setup page
8. CI workflow

### Suggested order for one developer

T001 through T052 in this order: T001–T012, T046–T052, T013–T045. Parallel markers are for a second worker, not a reason to skip a failing test.

---

## Notes

- [P] tasks use different files and do not depend on each other
- Each user story has an independent test written in its phase
- Confirm a new test fails before writing the code that makes it pass
- Do not download models in tests
- Commit after each task or logical group when the person asks for commits
