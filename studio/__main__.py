import argparse
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from studio import config
from studio.onboarding.flow import run_flow


@dataclass(frozen=True)
class LaunchPlan:
    run_onboarding: bool
    serve: bool
    open_browser: bool
    url: str = config.STUDIO_URL


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
) -> LaunchPlan:
    parser = argparse.ArgumentParser(prog="studio")
    parser.add_argument("--onboard", action="store_true")
    parser.add_argument("--skip-onboard", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    root = Path(data_dir) if data_dir is not None else config.DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    interactive = sys.stdin.isatty() if isatty is None else isatty
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


def _open_later(opener, url: str) -> None:
    def wait_and_open() -> None:
        import socket

        for _ in range(50):
            try:
                with socket.create_connection((config.BIND_HOST, config.PORT), timeout=0.2):
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
