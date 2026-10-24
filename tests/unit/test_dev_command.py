from pathlib import Path

from studio.__main__ import DEV_URL, dev_commands, launch


def test_dev_flag_starts_both_without_questions_or_the_built_ui(tmp_path):
    started = []

    def boom(_prompt):
        raise AssertionError("asked for input")

    plan = launch(
        ["--dev"],
        isatty=True,
        opener=lambda _url: (_ for _ in ()).throw(AssertionError("browser")),
        serve=lambda: (_ for _ in ()).throw(AssertionError("served built UI")),
        data_dir=tmp_path,
        read_line=boom,
        dev=lambda open_browser: started.append(open_browser),
    )
    assert started == [True]
    assert plan.run_onboarding is False
    assert plan.open_browser is True
    assert plan.url == DEV_URL
    assert not (tmp_path / "onboarding.json").exists()


def test_dev_no_browser_skips_the_vite_page(tmp_path):
    started = []
    plan = launch(
        ["--dev", "--no-browser"],
        isatty=True,
        opener=lambda _url: (_ for _ in ()).throw(AssertionError("browser")),
        serve=lambda: None,
        data_dir=tmp_path,
        read_line=lambda _prompt: (_ for _ in ()).throw(AssertionError("asked")),
        dev=lambda open_browser: started.append(open_browser),
    )
    assert started == [False]
    assert plan.open_browser is False
    assert plan.url == DEV_URL


def test_dev_commands_bind_the_api_and_vite_to_loopback():
    api, ui, web = dev_commands(python="python3", npm="npm", web=Path("web"))
    assert api == ["python3", "-m", "studio", "--skip-onboard", "--no-browser"]
    assert ui == ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"]
    assert web == Path("web")
