import inspect

from studio.onboarding.commands import commands_for
import studio.onboarding.commands as commands_module


def test_each_operating_system_has_its_own_install_and_start_text():
    bundles = {
        "darwin": commands_for("darwin"),
        "windows": commands_for("Windows"),
        "linux": commands_for("linux"),
    }
    for runtime in ("ollama", "lmstudio", "llamacpp"):
        installs = {bundles[name][runtime]["install"] for name in bundles}
        starts = {bundles[name][runtime]["start"] for name in bundles}
        assert len(installs) == 3
        assert len(starts) == 3
    assert bundles["darwin"]["ollama"]["install"] == "brew install ollama"
    assert "ollama.com/download/windows" in bundles["windows"]["ollama"]["install"]
    assert "ollama.com/install.sh" in bundles["linux"]["ollama"]["install"]
    assert "127.0.0.1" in bundles["darwin"]["llamacpp"]["start"]
    assert "8080" in bundles["windows"]["llamacpp"]["start"]
    assert "1234" in bundles["linux"]["lmstudio"]["start"]


def test_command_module_does_not_launch_processes():
    source = inspect.getsource(commands_module)
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "Popen" not in source
