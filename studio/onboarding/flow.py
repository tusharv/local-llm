import json
from dataclasses import dataclass

from studio.config import STUDIO_URL
from studio.db import connect, create_endpoint, init_db, now_iso
from studio.onboarding.commands import commands_for
from studio.onboarding.detect import Detection, detect_runtimes, normalize_os


@dataclass
class FlowResult:
    completed: bool
    endpoint_id: int | None
    open_browser: bool
    url: str


def run_flow(
    *,
    data_dir,
    system: str,
    read_line,
    open_browser=None,
    probe=None,
) -> FlowResult:
    os_name = normalize_os(system)
    probe_fn = probe or (lambda: detect_runtimes(system=os_name))
    while True:
        detections = list(probe_fn())
        print(format_report(detections, os_name), flush=True)
        while True:
            choice = read_line("Choice: ").strip().lower()
            if choice == "r":
                break
            if choice == "s":
                _open(open_browser)
                return FlowResult(False, None, open_browser is not None, STUDIO_URL)
            if choice == "c":
                _write_record(data_dir, os_name, None, detections)
                _open(open_browser)
                return FlowResult(True, None, open_browser is not None, STUDIO_URL)
            if choice.isdigit():
                running = [item for item in detections if item.state == "running"]
                index = int(choice)
                if 1 <= index <= len(running):
                    endpoint_id = _save_endpoint(data_dir, running[index - 1])
                    _write_record(data_dir, os_name, endpoint_id, detections)
                    _open(open_browser)
                    return FlowResult(True, endpoint_id, open_browser is not None, STUDIO_URL)
            print("Enter a running server number, c, r, or s.", flush=True)


def format_report(detections: list[Detection], system: str) -> str:
    commands = commands_for(system)
    lines = ["Local model servers", ""]
    for item in detections:
        if item.state == "running":
            lines.append(f"{item.label}: running on {item.detail}")
        elif item.state == "stopped":
            lines.append(f"{item.label}: installed, stopped. {item.detail}")
            lines.append(f"Start: {commands[item.runtime]['start']}")
        else:
            lines.append(f"{item.label}: missing. {item.detail}")
            lines.append(f"Install: {commands[item.runtime]['install']}")
            lines.append(f"Start: {commands[item.runtime]['start']}")
        lines.append("")
    running = [item for item in detections if item.state == "running"]
    if running:
        lines.append("Running servers")
        for index, item in enumerate(running, start=1):
            lines.append(f"{index}. {item.label}")
        lines.append("Enter a number to save that server, c to continue with none, r to check again, or s to skip.")
    else:
        lines.append("No server is answering.")
        lines.append("Enter c to continue, r to check again, or s to skip.")
    lines.append("Studio will not run these commands.")
    return "\n".join(lines)


def _save_endpoint(data_dir, detection: Detection) -> int:
    db_path = data_dir / "studio.db"
    init_db(db_path)
    with connect(db_path) as conn:
        row = create_endpoint(
            conn,
            name=detection.label,
            base_url=f"http://127.0.0.1:{detection.port}/v1",
            kind=detection.kind,
            api_key=None,
            private_network_confirmed=False,
        )
    return int(row["id"])


def _write_record(data_dir, system: str, endpoint_id: int | None, detections: list[Detection]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "completed_at": now_iso(),
        "os": system,
        "endpoint_id": endpoint_id,
        "detections": [
            {"runtime": item.runtime, "state": item.state, "detail": item.detail} for item in detections
        ],
    }
    (data_dir / "onboarding.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _open(open_browser) -> None:
    if open_browser is not None:
        open_browser(STUDIO_URL)
