import argparse
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from studio import config
from studio.onboarding.flow import run_flow

DEV_PORT = 5173
DEV_URL = f"http://{config.BIND_HOST}:{DEV_PORT}"


@dataclass(frozen=True)
class LaunchPlan:
    run_onboarding: bool
    serve: bool
    open_browser: bool
    url: str = config.STUDIO_URL


def dev_commands(*, python: str, npm: str, web: Path) -> tuple[list[str], list[str], Path]:
    api = [python, "-m", "studio", "--skip-onboard", "--no-browser"]
    ui = [npm, "run", "dev", "--", "--host", config.BIND_HOST, "--port", str(DEV_PORT), "--strictPort"]
    return api, ui, web


def plan_launch(
    *,
    interactive: bool,
    onboard: bool,
    skip_onboard: bool,
    no_browser: bool,
    completed: bool,
) -> LaunchPlan:
    if not interactive:
        return LaunchPlan(run_onboarding=False, serve=True, open_browser=False)
    run_onboarding = (not skip_onboard) and (onboard or not completed)
    return LaunchPlan(
        run_onboarding=run_onboarding,
        serve=True,
        open_browser=not no_browser,
    )


def launch(
    argv: list[str] | None = None,
    *,
    isatty: bool | None = None,
    opener=None,
    serve=None,
    data_dir: Path | None = None,
    read_line=None,
    probe=None,
    dev=None,
) -> LaunchPlan:
    parser = argparse.ArgumentParser(prog="studio")
    parser.add_argument("--onboard", action="store_true")
    parser.add_argument("--skip-onboard", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--dev", action="store_true", help="start the API and the Vite dev server")
    args = parser.parse_args(argv)
    root = Path(data_dir) if data_dir is not None else config.DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    interactive = sys.stdin.isatty() if isatty is None else isatty
    if args.dev:
        open_browser = interactive and not args.no_browser
        if dev is None:
            _serve_dev(open_browser=open_browser)
        else:
            dev(open_browser)
        return LaunchPlan(run_onboarding=False, serve=True, open_browser=open_browser, url=DEV_URL)
    completed = (root / "onboarding.json").exists()
    plan = plan_launch(
        interactive=interactive,
        onboard=args.onboard,
        skip_onboard=args.skip_onboard,
        no_browser=args.no_browser,
        completed=completed,
    )
    browser = opener if opener is not None else webbrowser.open
    if plan.run_onboarding:
        run_flow(
            data_dir=root,
            system=_system(),
            read_line=read_line or input,
            open_browser=browser if plan.open_browser and serve is not None else None,
            probe=probe,
        )
        if plan.open_browser and serve is None:
            _open_later(browser, plan.url)
    elif plan.open_browser and serve is None:
        _open_later(browser, plan.url)
    elif plan.open_browser:
        browser(plan.url)
    if serve is None:
        _serve()
    else:
        serve()
    return plan


def main(argv: list[str] | None = None) -> None:
    launch(argv)


def _serve() -> None:
    import uvicorn

    uvicorn.run(
        "studio.main:create_app",
        factory=True,
        host=config.BIND_HOST,
        port=config.PORT,
    )


def _serve_dev(*, open_browser: bool) -> None:
    web = Path(__file__).resolve().parent.parent / "web"
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm was not found. Install Node.js 20 or newer, then run this command from the repository root.")
    if not (web / "package.json").is_file():
        raise SystemExit(f"The web app was not found at {web}.")
    if not (web / "node_modules").is_dir():
        raise SystemExit("Web dependencies are missing. From the web directory, run: npm install")
    api_cmd, ui_cmd, web = dev_commands(python=sys.executable, npm=npm, web=web)
    print(f"API {config.STUDIO_URL}", flush=True)
    print(f"UI  {DEV_URL}", flush=True)
    api = subprocess.Popen(api_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    ui = subprocess.Popen(ui_cmd, cwd=web, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    if open_browser:
        _open_later(webbrowser.open, DEV_URL, port=DEV_PORT)
    for name, proc in (("api", api), ("ui", ui)):
        threading.Thread(target=_pipe, args=(name, proc), daemon=True).start()
    code = 0
    try:
        while api.poll() is None and ui.poll() is None:
            time.sleep(0.2)
        finished = api if api.poll() is not None else ui
        code = 0 if finished.returncode is None else finished.returncode
    except KeyboardInterrupt:
        code = 0
    finally:
        _stop_process(ui)
        _stop_process(api)
    raise SystemExit(code)


def _pipe(name: str, proc: subprocess.Popen[str]) -> None:
    if proc.stdout is None:
        return
    for line in proc.stdout:
        print(f"[{name}] {line}", end="", flush=True)


def _stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _open_later(opener, url: str, *, port: int | None = None) -> None:
    target = config.PORT if port is None else port

    def wait_and_open() -> None:
        import socket

        for _ in range(50):
            try:
                with socket.create_connection((config.BIND_HOST, target), timeout=0.2):
                    opener(url)
                    return
            except OSError:
                time.sleep(0.1)

    threading.Thread(target=wait_and_open, daemon=True).start()


def _system() -> str:
    import platform

    return platform.system()


if __name__ == "__main__":
    main()
