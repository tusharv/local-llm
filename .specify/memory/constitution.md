# Local LLM Studio Constitution

## 1. Privacy stays on the device

Studio binds to `127.0.0.1`. Chat text, images, and benchmark rows live in `./data`. Public cloud model hosts are rejected. A private-network engine URL requires an explicit confirm because prompts then leave this machine.

## 2. Any local OpenAI-compatible engine

Chat, model list, vision, and benchmarks use `/v1/models` and `/v1/chat/completions`. Ollama is a preset that adds pull, delete, and native capability flags. Studio does not install or launch model runtimes. The first-run terminal flow only checks PATH and local ports, prints install and start commands, then starts Studio and opens its own web page.

## 3. macOS, Windows, and Linux

Paths use `pathlib`. After download, `python -m studio` is the first command on macOS, Windows, and Linux. That command runs the terminal onboarding once, then serves the UI at `http://127.0.0.1:8000`. Automated tests run on Ubuntu, Windows, and macOS.

## 4. Benchmarks describe this machine

Record time to first token and tokens per second for one user, one model at a time. Label the numbers as speed on this server and tokenizer. Do not present them as answer quality.

## 5. Tests before calling a story done

Story behavior is covered with pytest against a temp directory and a mocked HTTP server. Tests do not download models or require a GPU.

## 6. v1 stays small

Out of scope: a native client per runtime, a judge model, RAG, voice, accounts, image generation, and concurrency benchmarks.
