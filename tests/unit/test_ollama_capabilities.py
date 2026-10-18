from studio.engines.ollama import resolve_vision


def test_native_vision_capability():
    vision, source = resolve_vision(
        override=None,
        capabilities=["completion", "vision"],
        family="llama",
        model_name="custom",
        probe=None,
    )
    assert vision is True
    assert source == "capabilities"


def test_family_fallback_when_capabilities_are_missing():
    vision, source = resolve_vision(
        override=None,
        capabilities=None,
        family="llava",
        model_name="llava:7b",
        probe=None,
    )
    assert vision is True
    assert source == "family"


def test_missing_capabilities_and_unknown_family():
    vision, source = resolve_vision(
        override=None,
        capabilities=None,
        family=None,
        model_name="llama3:8b",
        probe=None,
    )
    assert vision is False
    assert source == "unknown"


def test_override_off_wins_over_capability():
    vision, source = resolve_vision(
        override="off",
        capabilities=["vision"],
        family="llava",
        model_name="llava",
        probe="vision",
    )
    assert vision is False
    assert source == "override"
