# Local LLM Studio

Local LLM Studio is a private chat, model list, vision check, and speed benchmark for a model server running on your own machine. It speaks the OpenAI-compatible `/v1` API, so it works with Ollama, LM Studio, llama.cpp, and any other local server that implements those routes. Ollama is a preset that can also pull a model, delete a model, and read native vision flags.

Studio binds to `127.0.0.1:8000`. Chats, images, and benchmark rows stay in `./data`. It does not install or start Ollama, LM Studio, or llama.cpp. The first run prints the commands for your operating system. You copy them into a terminal yourself.

The same Studio install is used on macOS, Windows, and Linux.

## Install Studio

You need Python 3.11 or newer and Node.js 20 or newer.

```text
python -m pip install -e ".[dev]"
cd web
npm install
npm run build
cd ..
python -m studio
```

Open `http://127.0.0.1:8000`. Do not use `localhost` as the address. On Windows, `localhost` often resolves to IPv6 while Studio listens on IPv4.

While developing the UI, start the API and Vite together:

```text
python -m studio --dev
```

The API listens on `http://127.0.0.1:8000`. Vite serves the UI on `http://127.0.0.1:5173` and proxies `/api` to the API. Ctrl+C stops both. `--dev` skips the first-run questions.

Useful flags:

- `python -m studio --onboard` runs the first-run questions again
- `python -m studio --skip-onboard` starts the server once without the questions
- `python -m studio --no-browser` starts the server without opening a browser
- `python -m studio --dev --no-browser` starts the API and Vite without opening a page

If stdin is not a terminal, Studio does not wait for input and does not open a browser.

## Privacy

Studio listens only on `127.0.0.1`. Transcripts, uploaded images, and benchmark rows are stored under `./data` on this computer. A loopback server URL is saved immediately. A private-network URL is saved only after you confirm it, because prompts then leave this machine. Public cloud hosts, including `https://api.openai.com/v1`, are rejected. There is no account and no telemetry.

## Connect a server

Start the model server yourself, then save its `/v1` URL in Setup.

| Server | URL | Kind |
| --- | --- | --- |
| Ollama | `http://127.0.0.1:11434/v1` | Ollama |
| LM Studio | `http://127.0.0.1:1234/v1` | OpenAI-compatible |
| llama.cpp | `http://127.0.0.1:8080/v1` | OpenAI-compatible |

Any other local OpenAI-compatible server uses kind OpenAI-compatible and whatever port that server prints. Pull and delete stay hidden for that kind. Load the model in that runtime, then refresh Models.

## Ollama

Ollama's OpenAI routes and its native pull, delete, and capability routes share port `11434`.

### macOS

Install:

```text
brew install ollama
```

Start:

```text
ollama serve
```

Save `http://127.0.0.1:11434/v1` with kind Ollama.

### Windows

Install: download the Ollama installer for Windows from https://ollama.com/download/windows and run it.

Start, in PowerShell:

```text
ollama serve
```

Save `http://127.0.0.1:11434/v1` with kind Ollama.

### Linux

Install:

```text
curl -fsSL https://ollama.com/install.sh | sh
```

Start, in a terminal:

```text
ollama serve
```

Save `http://127.0.0.1:11434/v1` with kind Ollama.

## LM Studio

LM Studio serves an OpenAI-compatible API on port `1234` after you start the local server in the Developer tab. Studio cannot start that server for you.

### macOS

Install: download LM Studio for macOS from https://lmstudio.ai and move LM Studio.app to `/Applications`.

Start: open LM Studio on macOS, open the Developer tab, and start the local server on port `1234`.

Save `http://127.0.0.1:1234/v1` with kind OpenAI-compatible.

### Windows

Install: download LM Studio for Windows from https://lmstudio.ai and run the installer.

Start: open LM Studio on Windows, open the Developer tab, and start the local server on port `1234`.

Save `http://127.0.0.1:1234/v1` with kind OpenAI-compatible.

### Linux

Install: download LM Studio for Linux from https://lmstudio.ai.

Start: open LM Studio on Linux, open the Developer tab, and start the local server on port `1234`.

Save `http://127.0.0.1:1234/v1` with kind OpenAI-compatible.

## llama.cpp

llama.cpp's `llama-server` speaks `/v1` on the port you pass. The examples below use `8080` and `127.0.0.1`. Replace `MODEL.gguf` with a model file you already have.

### macOS

Install:

```text
brew install llama.cpp
```

Start:

```text
llama-server -m MODEL.gguf --host 127.0.0.1 --port 8080
```

Save `http://127.0.0.1:8080/v1` with kind OpenAI-compatible.

### Windows

Install: download a llama.cpp Windows build from https://github.com/ggml-org/llama.cpp/releases and unzip it.

Start:

```text
llama-server.exe -m MODEL.gguf --host 127.0.0.1 --port 8080
```

Save `http://127.0.0.1:8080/v1` with kind OpenAI-compatible.

### Linux

Install: build llama.cpp from https://github.com/ggml-org/llama.cpp or install the `llama-server` package for your distribution.

Start:

```text
llama-server -m MODEL.gguf --host 127.0.0.1 --port 8080
```

Save `http://127.0.0.1:8080/v1` with kind OpenAI-compatible.

## Memory

About 8 GB of RAM suits a 3B model. About 16 GB suits a 7B–8B Q4 model plus a small vision model. Those are examples, not a recommendation of a particular file. Pull or load the model in the runtime you chose, then refresh Models.

## What the pages do

Setup shows whether the saved server answers, how many models it has, and an Ollama pull box when the kind is Ollama. A stopped server stays on the page with the `127.0.0.1` hint so you can start it and refresh.

Chat streams a reply and reloads the same transcript from `./data`. Image attach appears only when the model is marked as able to see images. Deleting a conversation deletes its image files.

Models lists ids from `GET /v1/models`. Vision comes from an Ollama capability, a known vision family name, a vision-check probe, or the override you set. Pull and delete are Ollama only.

Benchmarks run one model at a time. A discarded warmup is on by default. Repeat count is 1 or 3. The table is time to first token and tokens per second for this server and tokenizer. It is not a quality score. Export downloads the stored rows as JSON. Runs from a different suite version are not compared.

## Troubleshooting

- The browser cannot connect. Open `http://127.0.0.1:8000`, not `http://localhost:8000`.
- Setup says the endpoint is down. Start the model server in its own terminal. Studio will not run `ollama serve` or `llama-server` for you.
- Saving `https://api.openai.com/v1` fails. Point Studio at a loopback or confirmed private-network `/v1` URL.
- A private-network URL is refused. Check the confirm box. The page will say that prompts are sent to that host.
- Chat says the model is unavailable. The conversation stays readable. Pick a model that is still installed and send again.
- A second benchmark is rejected while one is still marked running. Wait for it to finish.
- The first benchmark sample is slower because the runtime is loading the model. Leave warmup on unless you want that sample stored.

## Tests

```text
pytest
```

Tests use a temporary directory and a mocked HTTP server. They do not download a model and do not need a GPU. The same command runs on Ubuntu, Windows, and macOS in GitHub Actions.

## License

MIT. See `LICENSE`.

## Visual benchmark reports

Benchmarks now offers three suite-v2 profiles:

- **General suite:** quick response, explanation, reasoning, Python, JavaScript, and an image-understanding task when the model supports vision.
- **Code generation:** two fixed Python and JavaScript prompts. Generated code is displayed as text, never executed or graded.
- **Image generation:** one fixed product-photo prompt requesting a 512 × 512 image. Choose a saved local image server and its image model. The server must implement `POST /v1/images/generations` and return PNG, JPEG, or WebP in `data[0].b64_json`. Image URLs are not fetched. Unsupported endpoints produce a failed report with an explanation.

Each profile supports one or three repetitions. Warmup is excluded from measurements; image warmup is off by default because it generates an extra image. Image requests have a 180-second response timeout and an 8 MB decoded image limit. Generated images stay under `data/uploads`.

Reports show median response time, effective throughput, completion counts, per-task charts, and output previews. Effective throughput is output tokens divided by **the full request duration**, including the initial wait. If token usage is absent, streamed chunks are used and labeled as estimates. Images report total time instead of tokens per second. Completion means a response was returned, not that the code or image is correct.

Choose a previous compatible run to compare response time. Compatibility requires the same suite, profile, case set and sample counts, repeat count, warmup setting, and token-count basis, with all cases successful. Legacy suite-v1 reports remain readable. Export JSON preserves measurements and local image references; **Print / Save PDF** opens the browser print dialog with the report and expanded output previews.

### Model downloads

Pulling a model from Setup or Models starts a Studio background job. Switching pages or refreshing reconnects to its saved progress. Only one model download per server runs at a time; repeating the same request returns the existing job. Keep Studio and Ollama running until the download finishes. If Studio restarts mid-download, the saved status explains the interruption; pull again to let Ollama reuse its downloaded data.
