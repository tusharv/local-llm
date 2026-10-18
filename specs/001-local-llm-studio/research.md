# Research: Local LLM Studio

## Decision: OpenAI-compatible `/v1` is the engine contract

**Rationale**: Ollama, LM Studio, llama.cpp server, vLLM, and LocalAI all expose `GET /v1/models` and `POST /v1/chat/completions`. One client covers chat, listing, vision input, and benchmarks.

**Alternatives considered**:

- Ollama only. Matches the development machine and gives pull, delete, and capability flags. It excludes the other local servers the product has to support.
- A native client per runtime. More metadata, and a large incompatible surface. v1 would miss the next server someone installs.

## Decision: Ollama extras are a preset, not the core

**Rationale**: Pull, delete, and `capabilities` are not in the OpenAI API. Kind `ollama` calls native `/api/show`, streamed pull, and delete. Kind `openai` lists models and chats only. The person loads models in that other app, then refreshes.

**Alternatives considered**: Hiding model management entirely. That makes Ollama harder to use from the same UI that already knows the server is Ollama.

## Decision: Measure speed in the Studio client

**Rationale**: Ollama's final chunk can include `eval_duration`. Other servers do not. Time to first token is the delay until the first content delta. Tokens per second uses `usage.completion_tokens` when the stream sends it, and the content-chunk count otherwise. A discarded warmup is on by default because the first load is slower.

**Alternatives considered**: Reading Ollama timings only. Those numbers would not compare with LM Studio or llama.cpp. A second judge model for quality. That loads another model on a 16 GB machine and is out of v1. The UI says the numbers are not a quality score.

## Decision: First run is a terminal conversation, then the browser

**Rationale**: After download, `python -m studio` is the only command a person needs to remember. The flow checks `shutil.which` and the three loopback ports, prints a short status, and prints install or start commands for the current OS. The person copies those commands into the same or another terminal. Studio then saves a chosen running endpoint if they pick one, writes `data/onboarding.json`, starts itself, and opens `http://127.0.0.1:8000` with `webbrowser`. Prompts use `input()` so the same code runs in Terminal, PowerShell, and cmd. If stdin is not a terminal, the flow does not wait and does not open a browser.

**Alternatives considered**: Running the installers from Studio. That is a different command on every OS and would start software the person has not chosen to run. A browser-only wizard as the first step. The web UI cannot show install commands before a runtime exists, and a stopped machine still needs the terminal report. A curses or third-party TUI. It breaks more often in Windows consoles than plain prompts.

## Decision: Do not spawn runtimes

**Rationale**: Studio only sends HTTP. Starting Ollama or llama.cpp from the app hits Windows `.cmd` shims, shell quoting, and process trees that differ from macOS and Linux. The README tells the person how to install and start the runtime on each OS.

**Alternatives considered**: A setup button that runs `ollama serve`. It fails differently on each OS and violates the constitution.

## Decision: `127.0.0.1` and `./data`

**Rationale**: On Windows, `localhost` often resolves to IPv6 while the server listens on IPv4. Binding and documenting `127.0.0.1` avoids that. `./data` via `pathlib` is the same relative location on macOS, Windows, and Linux. Loopback engine URLs work immediately. Private-network URLs need a confirm control. Public cloud hosts are rejected.

**Alternatives considered**: Docker as the install path. It is optional for some runtimes and a poor requirement for a local GUI on all three operating systems.

## Decision: Tests are mocked and run on three OS images

**Rationale**: The development machine is an Apple M1 with 16 GB. A click-through happens there. Confidence for Windows and Linux comes from pytest using `tmp_path` and a fake HTTP server, executed on `ubuntu-latest`, `windows-latest`, and `macos-latest`. No test downloads a model.
