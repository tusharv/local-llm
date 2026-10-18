import os
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Runtime:
    runtime: str
    label: str
    binaries: tuple[str, ...]
    port: int
    kind: str


@dataclass(frozen=True)
class Detection:
    runtime: str
    label: str
    state: str
    detail: str
    port: int
    kind: str


RUNTIMES = (
    Runtime("ollama", "Ollama", ("ollama",), 11434, "ollama"),
    Runtime("lmstudio", "LM Studio", ("lms",), 1234, "openai"),
    Runtime("llamacpp", "llama.cpp", ("llama-server",), 8080, "openai"),
)


def detect_runtimes(
    *,
    which=None,
    port_open=None,
    system: str | None = None,
    app_exists=None,
) -> list[Detection]:
    which_fn = which or shutil.which
    port_fn = port_open or tcp_open
    exists = app_exists or (lambda path: Path(path).exists())
    current = system or normalize_os(os_name())
    found: list[Detection] = []
    for runtime in RUNTIMES:
        answering = bool(port_fn(runtime.port))
        program = _program_found(runtime, current, which_fn, exists)
        if answering:
            state = "running"
            detail = f"127.0.0.1:{runtime.port}"
        elif program:
            state = "stopped"
            detail = "program found, port closed"
        else:
            state = "missing"
            detail = "not installed"
        found.append(
            Detection(
                runtime.runtime,
                runtime.label,
                state,
                detail,
                runtime.port,
                runtime.kind,
            )
        )
    return found


def tcp_open(port: int, host: str = "127.0.0.1", timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def normalize_os(system: str) -> str:
    name = system.lower()
    if name in {"darwin", "mac", "macos"}:
        return "darwin"
    if name.startswith("win"):
        return "windows"
    return "linux"


def os_name() -> str:
    return __import__("platform").system()


def _program_found(runtime: Runtime, system: str, which, exists) -> bool:
    if any(which(name) for name in runtime.binaries):
        return True
    return any(exists(path) for path in _app_paths(runtime.runtime, system))


def _app_paths(runtime: str, system: str) -> list[Path]:
    if runtime != "lmstudio":
        return []
    if system == "darwin":
        return [Path("/Applications/LM Studio.app")]
    if system == "windows":
        local = os.environ.get("LOCALAPPDATA", "")
        if not local:
            return []
        return [Path(local) / "Programs" / "LM Studio"]
    return [Path.home() / ".local" / "share" / "lm-studio"]
