import json

from studio.config import STUDIO_URL
from studio.db import connect, get_endpoint
from studio.onboarding.detect import Detection, detect_runtimes
from studio.onboarding.flow import format_report, run_flow
from studio.__main__ import launch


def _line(runtime, label, state, port, kind, detail):
    return Detection(runtime, label, state, detail, port, kind)


def _set():
    return [
        _line("ollama", "Ollama", "running", 11434, "ollama", "127.0.0.1:11434"),
        _line("lmstudio", "LM Studio", "missing", 1234, "openai", "not installed"),
        _line("llamacpp", "llama.cpp", "running", 8080, "openai", "127.0.0.1:8080"),
    ]


def test_detects_running_stopped_and_missing():
    def which(name):
        return "/usr/bin/ollama" if name == "ollama" else None

    def port_open(port):
        return port == 1234

    found = detect_runtimes(which=which, port_open=port_open, system="linux", app_exists=lambda _path: False)
    assert {item.runtime: item.state for item in found} == {
        "ollama": "stopped",
        "lmstudio": "running",
        "llamacpp": "missing",
    }


def test_missing_prints_install_and_start_for_that_os():
    detections = [
        _line("ollama", "Ollama", "missing", 11434, "ollama", "not installed"),
        _line("lmstudio", "LM Studio", "running", 1234, "openai", "127.0.0.1:1234"),
        _line("llamacpp", "llama.cpp", "running", 8080, "openai", "127.0.0.1:8080"),
    ]
    text = format_report(detections, "darwin")
    assert "Ollama: missing" in text
    assert "brew install ollama" in text
    assert "ollama serve" in text


def test_stopped_prints_start_and_not_install():
    detections = [
        _line("ollama", "Ollama", "stopped", 11434, "ollama", "program found, port closed"),
        _line("lmstudio", "LM Studio", "running", 1234, "openai", "127.0.0.1:1234"),
        _line("llamacpp", "llama.cpp", "running", 8080, "openai", "127.0.0.1:8080"),
    ]
    text = format_report(detections, "darwin")
    assert "installed, stopped" in text
    assert "ollama serve" in text
    assert "brew install ollama" not in text


def test_choice_saves_endpoint_record_and_browser(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("command executed")

    monkeypatch.setattr("subprocess.run", boom)
    monkeypatch.setattr("os.system", boom)
    opened = []
    result = run_flow(
        data_dir=tmp_path,
        system="darwin",
        read_line=lambda _prompt: "2",
        open_browser=opened.append,
        probe=lambda: _set(),
    )
    assert result.completed is True
    assert result.url == STUDIO_URL
    assert opened == [STUDIO_URL]
    record = json.loads((tmp_path / "onboarding.json").read_text(encoding="utf-8"))
    assert record["os"] == "darwin"
    assert record["endpoint_id"] == result.endpoint_id
    assert record["detections"][2]["state"] == "running"
    with connect(tmp_path / "studio.db") as conn:
        endpoint = get_endpoint(conn, result.endpoint_id)
    assert endpoint["base_url"] == "http://127.0.0.1:8080/v1"
    assert endpoint["kind"] == "openai"


def test_reprobe_then_continue_without_endpoint(tmp_path):
    calls = {"n": 0}

    def probe():
        calls["n"] += 1
        if calls["n"] == 1:
            return [_line("ollama", "Ollama", "missing", 11434, "ollama", "not installed")]
        return [_line("ollama", "Ollama", "running", 11434, "ollama", "127.0.0.1:11434")]

    answers = iter(["r", "c"])
    result = run_flow(
        data_dir=tmp_path,
        system="linux",
        read_line=lambda _prompt: next(answers),
        open_browser=lambda _url: None,
        probe=probe,
    )
    assert calls["n"] == 2
    assert result.endpoint_id is None
    record = json.loads((tmp_path / "onboarding.json").read_text(encoding="utf-8"))
    assert record["endpoint_id"] is None


def test_skip_does_not_write_completion_file(tmp_path):
    result = run_flow(
        data_dir=tmp_path,
        system="windows",
        read_line=lambda _prompt: "s",
        open_browser=lambda _url: None,
        probe=lambda: _set(),
    )
    assert result.completed is False
    assert not (tmp_path / "onboarding.json").exists()


def test_second_run_skips_questions_and_opens_browser(tmp_path):
    (tmp_path / "onboarding.json").write_text("{}\n", encoding="utf-8")
    opened = []

    def boom(_prompt):
        raise AssertionError("asked for input")

    launch([], isatty=True, opener=opened.append, serve=lambda: None, data_dir=tmp_path, read_line=boom)
    assert opened == [STUDIO_URL]


def test_non_tty_does_not_block_or_open_browser(tmp_path):
    opened = []

    def boom(_prompt):
        raise AssertionError("blocked on input")

    launch([], isatty=False, opener=opened.append, serve=lambda: None, data_dir=tmp_path, read_line=boom)
    assert opened == []
    assert not (tmp_path / "onboarding.json").exists()


def test_skip_onboard_flag_skips_once(tmp_path):
    opened = []

    def boom(_prompt):
        raise AssertionError("asked for input")

    launch(
        ["--skip-onboard"],
        isatty=True,
        opener=opened.append,
        serve=lambda: None,
        data_dir=tmp_path,
        read_line=boom,
    )
    assert opened == [STUDIO_URL]
    assert not (tmp_path / "onboarding.json").exists()


def test_onboard_flag_runs_again(tmp_path):
    (tmp_path / "onboarding.json").write_text('{"completed_at":"old"}\n', encoding="utf-8")
    launch(
        ["--onboard", "--no-browser"],
        isatty=True,
        opener=lambda _url: (_ for _ in ()).throw(AssertionError("browser")),
        serve=lambda: None,
        data_dir=tmp_path,
        read_line=lambda _prompt: "c",
        probe=lambda: [_line("ollama", "Ollama", "missing", 11434, "ollama", "not installed")],
    )
    record = json.loads((tmp_path / "onboarding.json").read_text(encoding="utf-8"))
    assert record["endpoint_id"] is None
    assert record["completed_at"] != "old"
