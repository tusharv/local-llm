import pytest

from studio.engines.openai_compatible import compute_speed


def test_ttft_and_usage_tokens_per_second():
    speed = compute_speed(
        started=0,
        ended=1.25,
        first_token=0.25,
        content_chunks=4,
        usage={"completion_tokens": 10, "prompt_tokens": 6},
        text="counted",
    )
    assert speed.ttft_ms == 250
    assert speed.prompt_tokens == 6
    assert speed.output_tokens == 10
    assert speed.tokens_per_second == pytest.approx(8.0)


def test_chunk_count_fallback_when_usage_is_missing():
    speed = compute_speed(
        started=0,
        ended=2.5,
        first_token=0.5,
        content_chunks=4,
        usage=None,
        text="abcd",
    )
    assert speed.output_tokens == 4
    assert speed.prompt_tokens is None
    assert speed.tokens_per_second == pytest.approx(4 / 2.5)


def test_no_token_omits_tokens_per_second():
    speed = compute_speed(
        started=0,
        ended=1,
        first_token=None,
        content_chunks=0,
        usage=None,
        text="",
    )
    assert speed.ttft_ms is None
    assert speed.tokens_per_second is None
    assert speed.error
