COMMANDS = {
    "darwin": {
        "ollama": {
            "install": "brew install ollama",
            "start": "ollama serve",
        },
        "lmstudio": {
            "install": "Download LM Studio for macOS from https://lmstudio.ai and move LM Studio.app to /Applications.",
            "start": "Open LM Studio on macOS, open the Developer tab, and start the local server on port 1234.",
        },
        "llamacpp": {
            "install": "brew install llama.cpp",
            "start": "On macOS, run: llama-server -m MODEL.gguf --host 127.0.0.1 --port 8080",
        },
    },
    "windows": {
        "ollama": {
            "install": "Download the Ollama installer for Windows from https://ollama.com/download/windows and run it.",
            "start": "In PowerShell, run: ollama serve",
        },
        "lmstudio": {
            "install": "Download LM Studio for Windows from https://lmstudio.ai and run the installer.",
            "start": "Open LM Studio on Windows, open the Developer tab, and start the local server on port 1234.",
        },
        "llamacpp": {
            "install": "Download a llama.cpp Windows build from https://github.com/ggml-org/llama.cpp/releases and unzip it.",
            "start": "llama-server.exe -m MODEL.gguf --host 127.0.0.1 --port 8080",
        },
    },
    "linux": {
        "ollama": {
            "install": "curl -fsSL https://ollama.com/install.sh | sh",
            "start": "In a terminal, run: ollama serve",
        },
        "lmstudio": {
            "install": "Download LM Studio for Linux from https://lmstudio.ai.",
            "start": "Open LM Studio on Linux, open the Developer tab, and start the local server on port 1234.",
        },
        "llamacpp": {
            "install": "Build llama.cpp from https://github.com/ggml-org/llama.cpp or install the llama-server package for your distribution.",
            "start": "On Linux, run: llama-server -m MODEL.gguf --host 127.0.0.1 --port 8080",
        },
    },
}


def commands_for(system: str) -> dict[str, dict[str, str]]:
    from studio.onboarding.detect import normalize_os

    name = normalize_os(system)
    return COMMANDS[name]
