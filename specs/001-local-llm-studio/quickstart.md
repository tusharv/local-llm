# Quickstart: Local LLM Studio

Validation for a developer on macOS, Windows, or Linux. The product README is the longer guide written in task T042. The download experience is the terminal flow in task T046 through T052.

## First run

From the repository root, after `python -m pip install -e ".[dev]"` and `npm run build` inside `web/`:

```text
python -m studio
```

The terminal reports Ollama, LM Studio, and llama.cpp, prints commands for anything missing or stopped, asks which running server to save, then opens `http://127.0.0.1:8000`. Do not use `localhost` as the documented address.

Useful flags:

- `--onboard` runs the questions again
- `--skip-onboard` starts the server without questions
- `--no-browser` starts the server without opening a browser
- `--dev` starts the API and the Vite dev server together

A non-interactive process does not wait and does not open a browser.

## Install Studio for development

From the repository root:

```text
python -m pip install -e ".[dev]"
cd web
npm install
npm run build
cd ..
python -m studio
```

Open `http://127.0.0.1:8000`. Do not use `localhost` as the documented address.

Dev loop, one command from the repository root:

```text
python -m studio --dev
```

The API listens on `http://127.0.0.1:8000`. Vite serves the UI on `http://127.0.0.1:5173` and proxies `/api` to the API. Ctrl+C stops both. `--dev` skips the first-run questions.

## Connect a runtime

Start one local server yourself. Studio will not start it.

- Ollama: `http://127.0.0.1:11434/v1`, kind `ollama`
- LM Studio: `http://127.0.0.1:1234/v1`, kind `openai`
- llama.cpp server: `http://127.0.0.1:8080/v1`, kind `openai`

On this Mac, Ollama 0.40.2 is installed and may be stopped. Start it, pull a small text model and a small vision model if you want a live click-through, then use the Ollama preset.

## Checks

1. A first `python -m studio` in a terminal prints a status line for Ollama, LM Studio, and llama.cpp, then opens the web UI.
2. The printed install or start commands match the current OS, and Studio does not run them.
3. Setup shows the endpoint down before the runtime is started, and up after it is.
4. Saving `https://api.openai.com/v1` is refused.
5. A chat round trip survives a browser refresh.
6. Image attach appears only for a vision-flagged model. Deleting that conversation removes the file under `data/uploads`.
7. A benchmark run stores time to first token and tokens per second, and the page says those numbers are not a quality score.
8. Pull and delete appear for the Ollama preset and do not appear for LM Studio or llama.cpp.

## Tests

```text
pytest
```

No model download and no GPU. The same command is the GitHub Actions job on Ubuntu, Windows, and macOS.
