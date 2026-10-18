# Feature Specification: Local LLM Studio

**Feature Branch**: `001-local-llm-studio`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "Open-source local LLM system with a web UI. Privacy-first chat, try different models, check multimodal capability, a step-by-step local setup guide, and a model benchmarking tool. Any local LLM, not only Ollama. macOS, Windows, and Linux."

## User Scenarios & Testing

### User Story 6 - First-run terminal onboarding (Priority: P1)

A person downloads the project and runs `python -m studio`. A terminal conversation shows which local model servers are already installed or running, prints the commands to install or start whatever is missing, lets them pick a server that is already up, and then opens the local web UI.

**Why this priority**: This is the first thing a person sees after download. The README remains the long guide. The terminal flow is the guided start.

**Independent Test**: With a fake PATH and fake port probes, run the flow on scripted input for macOS, Windows, and Linux. Confirm it prints that platform's install commands, does not execute them, saves the chosen running endpoint, records completion, and asks the browser opener to go to `http://127.0.0.1:8000`. A second run skips the questions. A non-interactive stdin skips the questions and does not open a browser.

**Acceptance Scenarios**:

1. **Given** a first run on macOS, Windows, or Linux, **When** `python -m studio` starts, **Then** the terminal lists Ollama, LM Studio, and llama.cpp as installed, running, stopped, or missing.
2. **Given** Ollama is missing, **When** the report prints, **Then** it shows the install command and the start command for that operating system, and it does not run either command.
3. **Given** Ollama's program is on PATH and port `11434` is closed, **When** the report prints, **Then** it shows the start command and does not show the install command as the next step.
4. **Given** two servers are answering on loopback, **When** the person picks one by number, **Then** Studio saves that endpoint and continues.
5. **Given** no server is answering, **When** the person chooses to continue, **Then** Studio still starts and opens `http://127.0.0.1:8000`.
6. **Given** onboarding already completed, **When** the person runs `python -m studio` again, **Then** the questions are skipped and the web UI opens. `python -m studio --onboard` runs the questions again.
7. **Given** stdin is not a terminal, **When** the process starts, **Then** it does not wait for input and does not open a browser.

---

### User Story 1 - Private chat with a local model (Priority: P1)

A person installs Studio, points it at a local model server, and chats. The transcript stays in a folder on that computer. They can switch models and keep earlier conversations.

**Why this priority**: Without a private chat against a local server, the rest of the product has nothing to manage or measure.

**Independent Test**: Save a loopback endpoint, mock a streaming chat completion, send a message, reload the conversation, and confirm the reply is stored only in the local database.

**Acceptance Scenarios**:

1. **Given** no saved endpoint, **When** the person adds `http://127.0.0.1:11434/v1` with kind Ollama, **Then** Studio stores it and can ask that server whether it is up.
2. **Given** a reachable endpoint with at least one model, **When** the person sends a chat message, **Then** the reply streams into the page and both turns are still there after refresh.
3. **Given** a base URL on a public cloud host, **When** the person tries to save it, **Then** Studio refuses and leaves the database unchanged.
4. **Given** a private-network URL, **When** the person saves it without the confirm control, **Then** Studio refuses. **When** they confirm, **Then** Studio saves it and the page states that prompts will be sent to that host.
5. **Given** an existing conversation, **When** the person deletes it, **Then** its messages are gone from the local database.

---

### User Story 2 - See and manage installed models (Priority: P2)

A person lists the models on the selected server, sees which ones can take images, and, on Ollama only, pulls or deletes a model.

**Why this priority**: Comparing models starts with knowing what is installed and which runtime can manage them.

**Independent Test**: Point at a mocked `/v1/models` list. Confirm a generic endpoint has no pull or delete. Confirm an Ollama endpoint exposes pull progress and delete, and that vision is detected from capabilities or a saved override.

**Acceptance Scenarios**:

1. **Given** a saved endpoint, **When** the person opens Models, **Then** they see the model ids returned by that server.
2. **Given** kind `ollama` and a model whose native details include vision, **When** the list loads, **Then** that model is marked as able to see images.
3. **Given** kind `openai`, **When** the person looks for pull or delete, **Then** those actions are absent and the page tells them to load the model in that runtime, then refresh.
4. **Given** a model, **When** the person sets the vision override, **Then** later chats and benchmarks use that override.

---

### User Story 3 - Check vision (Priority: P2)

A person attaches an image in chat when the model is marked as vision-capable, and can run one fixed vision check against a bundled picture.

**Why this priority**: Multimodal support is a stated reason to try one local model instead of another.

**Independent Test**: Post the bundled image question to a mocked vision model and to a mocked text model. The vision model returns an answer and timing. The text model is recorded as not vision-capable, and the chat page does not offer an attachment for it.

**Acceptance Scenarios**:

1. **Given** a vision-flagged model, **When** the person attaches an image and sends a message, **Then** the image is stored under the local data directory and sent only to the selected local endpoint.
2. **Given** a text-only model, **When** the person opens the composer, **Then** image attach is unavailable.
3. **Given** a vision-flagged model, **When** the person runs the vision check, **Then** they see the model's answer and the time it took.
4. **Given** a conversation with an image, **When** the person deletes that conversation, **Then** the image file is removed from the data directory.

---

### User Story 4 - Benchmark models on this machine (Priority: P2)

A person runs the same small prompt set against one installed model and compares the saved speed numbers with earlier runs.

**Why this priority**: The benchmarking tool is a separate product surface from chat. Speed has to be measured the same way on every local server.

**Independent Test**: Run the suite against a mocked stream that emits one delayed chunk and a final usage block. Confirm time to first token, tokens per second, suite version, endpoint, and model are stored, and that a second model is not started until the first finishes.

**Acceptance Scenarios**:

1. **Given** a selected model, **When** the person starts a benchmark, **Then** Studio runs the fixed text prompts one at a time and stores a run.
2. **Given** a vision-flagged model, **When** the run includes the vision case, **Then** that case uses the bundled image and the same timing fields.
3. **Given** two runs with the same suite version, **When** the person opens the comparison, **Then** they see time to first token and tokens per second per model, with the endpoint name visible.
4. **Given** a finished run, **When** the person exports it, **Then** they receive a JSON file that matches the stored rows.
5. **Given** the results page, **When** it renders, **Then** it states that the numbers are single-user speed for this server and tokenizer, not a quality score.

---

### User Story 5 - Set up Studio on macOS, Windows, or Linux (Priority: P3)

A person who has never run a local model follows the guide for their operating system, starts a runtime, and connects Studio.

**Why this priority**: The project is for other people. Chat can be demoed on one machine before the guide is finished, and the guide is what makes the other two operating systems real for a new user.

**Independent Test**: Read the README and complete the in-app setup checklist against a stopped server and then a mocked healthy server. Confirm each OS has install steps for Ollama, LM Studio, and llama.cpp, and that the documented URL uses `127.0.0.1`.

**Acceptance Scenarios**:

1. **Given** the README, **When** a person on macOS, Windows, or Linux looks up Ollama, LM Studio, or llama.cpp, **Then** they find an install step for that OS and the matching `/v1` port.
2. **Given** the Setup page and a stopped server, **When** it loads, **Then** it says the endpoint is down and how to start it, including the `127.0.0.1` versus `localhost` hint.
3. **Given** a healthy Ollama endpoint, **When** Setup loads, **Then** it shows version or reachability, installed models, and a pull action.
4. **Given** a healthy non-Ollama endpoint, **When** Setup loads, **Then** it shows reachability and models without a pull action.

### Edge Cases

- The local server closes the stream before any token. The chat turn stores an error, and a benchmark case stores an error without a tokens-per-second value.
- The first benchmark sample is a cold load. A discarded warmup is on by default and can be turned off.
- Ollama omits `capabilities`. Studio falls back to known vision family names, then to the probe and the override.
- A generic server omits `usage`. Tokens per second uses the streamed chunk count and the measured duration.
- Two benchmark requests arrive together. The second waits, or is rejected, until the first model finishes.
- The data directory is missing. Studio creates it.
- The person deletes a model in Ollama that a conversation still names. The conversation remains readable and the next send reports that the model is unavailable.
- Onboarding stdin is closed or is not a terminal. Studio does not block, does not open a browser, and leaves onboarding incomplete so a later terminal run still shows the flow.
- The person finishes onboarding with every runtime missing. The web UI still opens so Setup can be used after they run a printed command.

## Requirements

### Functional Requirements

- **FR-001**: Studio MUST serve a local web UI and HTTP API bound to `127.0.0.1`.
- **FR-002**: Users MUST be able to save, list, select, and delete local engine endpoints. Each endpoint has a name, a base URL ending in `/v1`, an optional API key, and a kind of `openai` or `ollama`.
- **FR-003**: Studio MUST reject public cloud base URLs. Loopback URLs MUST save with no extra confirm. Private-network URLs MUST save only after an explicit confirm.
- **FR-004**: Studio MUST list models from `GET {base}/v1/models` and stream chat from `POST {base}/v1/chat/completions`.
- **FR-005**: Studio MUST persist conversations and messages in a local database under `./data`, and MUST delete uploaded images when their conversation is deleted.
- **FR-006**: For an Ollama endpoint, Studio MUST show native model details when available, stream a model pull, and delete a model. Those two management actions MUST be unavailable for kind `openai`.
- **FR-007**: Studio MUST record whether a model can accept images, using native capabilities, a known vision family name, a cached probe, or a user override.
- **FR-008**: Users MUST be able to attach an image only for a vision-flagged model. The image MUST be stored locally and sent to the selected endpoint as an image data URL.
- **FR-009**: Users MUST be able to run a fixed vision check against a bundled image and see the answer plus timing.
- **FR-010**: Users MUST be able to run a versioned, single-user benchmark one model at a time, with an optional discarded warmup, repeat count 1 or 3, and stored time to first token, token counts, tokens per second, total time, output preview, and error.
- **FR-011**: Users MUST be able to compare saved runs of the same suite version and export one run as JSON.
- **FR-012**: The benchmark UI MUST describe the numbers as single-user speed for the recorded server and tokenizer.
- **FR-013**: The README and in-app Setup page MUST document install and connect steps for Ollama, LM Studio, and llama.cpp on macOS, Windows, and Linux, plus any other `/v1` server.
- **FR-014**: Studio MUST NOT install or start Ollama, LM Studio, llama.cpp, or any other model runtime. It MAY open the system browser to Studio's own `http://127.0.0.1:8000` address.
- **FR-015**: Automated tests MUST run without a GPU, a live model download, or a macOS-only API, and MUST be executed on Ubuntu, Windows, and macOS in CI.
- **FR-016**: The first interactive `python -m studio` MUST run a terminal onboarding flow before serving. Later runs MUST skip it unless `--onboard` is passed. `--skip-onboard` MUST skip it once.
- **FR-017**: Onboarding MUST report Ollama, LM Studio, and llama.cpp using a PATH check and a loopback probe of ports `11434`, `1234`, and `8080`. Each line MUST say installed, running, stopped, or missing.
- **FR-018**: For each stopped or missing runtime, onboarding MUST print install or start commands for the current operating system only, and MUST NOT execute those commands.
- **FR-019**: When at least one runtime is running, the person MUST be able to pick it by number and have it saved as an endpoint. They MUST also be able to continue with nothing saved.
- **FR-020**: After onboarding, Studio MUST serve the web UI and open `http://127.0.0.1:8000` in the browser unless `--no-browser` is set or stdin is not a terminal.

### Key Entities

- **Endpoint**: A local OpenAI-compatible server the person chose. Attributes: name, base URL, kind, optional API key, private-network confirm.
- **Conversation**: A chat thread bound to one endpoint and one model name.
- **Message**: One user or assistant turn. Optional local image path.
- **Model flag**: Per endpoint and model id. Vision override and last probe result.
- **Benchmark run**: One execution of a suite version against one endpoint and model. Status and timing summary.
- **Benchmark result**: One suite case inside a run. Kind `text` or `vision`, timing fields, short output preview, error.
- **Onboarding record**: A file at `./data/onboarding.json`, written when the person finishes the terminal flow. Attributes: completion time, operating system, optional chosen endpoint id, and the detection snapshot. Absent means the next interactive launch runs onboarding again.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A person can add a local endpoint and complete a streamed chat round trip, including a reload that shows the same transcript, without any account or cloud API key.
- **SC-002**: Saving `https://api.openai.com/v1` fails in the UI and in tests. Saving `http://127.0.0.1:11434/v1` succeeds.
- **SC-003**: On a mocked stream, stored time to first token matches the delay until the first content chunk, and tokens per second uses completion usage when present.
- **SC-004**: Deleting a conversation removes its image file from `./data`.
- **SC-005**: The README contains distinct install steps for macOS, Windows, and Linux for Ollama, LM Studio, and llama.cpp.
- **SC-006**: `pytest` passes on `ubuntu-latest`, `windows-latest`, and `macos-latest` with no model download.
- **SC-007**: A scripted first run prints the install command for a missing runtime on each of macOS, Windows, and Linux, saves a detected running endpoint when chosen, and records that the browser should open at `http://127.0.0.1:8000`. The test process does not execute the printed commands.

## Assumptions

- The person already has, or is willing to install, Python 3.11+, Node 20+, and one local model server.
- v1 is a single user on one computer. The local server may be on that computer or on a private-network host the person confirms.
- About 8 GB of RAM suits a 3B model. About 16 GB suits a 7B–8B Q4 model plus a small vision model. The guide states this and does not pick a model for the user beyond examples.
- Preset ports are Ollama `11434`, LM Studio `1234`, and llama.cpp `8080`.
- Development click-through happens on the current Apple M1 with 16 GB of RAM and Ollama 0.40.2. Windows and Linux confidence comes from the test matrix and the guide.
- License is MIT.
- Quality judging, RAG, voice, multi-user accounts, image generation, and concurrency benchmarks are out of v1.
