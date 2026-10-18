from pathlib import Path


def test_readme_documents_each_runtime_on_each_operating_system():
    readme = Path("README.md").read_text(encoding="utf-8")
    for runtime in ("## Ollama", "## LM Studio", "## llama.cpp"):
        assert runtime in readme
    for system in ("### macOS", "### Windows", "### Linux"):
        assert readme.count(system) >= 3
    assert "http://127.0.0.1:11434/v1" in readme
    assert "http://127.0.0.1:1234/v1" in readme
    assert "http://127.0.0.1:8080/v1" in readme
    assert "not a quality score" in readme
    assert "public cloud" in readme.lower() or "Public cloud" in readme
