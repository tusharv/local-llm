import pytest

from studio.engines.openai_compatible import compute_speed, measure_lines


def test_time_to_first_token_and_completion_usage():
    lines = [
        (0.4, 'data: {"choices":[{"delta":{"content":"Hi"}}]}'),
        (0.8, 'data: {"choices":[{"delta":{"content":"!"}}]}'),
        (1.0, 'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":3,"completion_tokens":2}}'),
        (1.0, "data: [DONE]"),
    ]
    speed = measure_lines(lines, started_at=0.0, ended_at=1.0)
    assert speed.ttft_ms == 400
    assert speed.text == "Hi!"
    assert speed.prompt_tokens == 3
    assert speed.output_tokens == 2
    assert speed.tokens_per_second == pytest.approx(2.0)
    assert speed.error is None


def test_usage_beats_chunk_count():
    speed = compute_speed(
        started=0,
        ended=1.25,
        first_token=0.25,
        content_chunks=4,
        usage={"prompt_tokens":3, "completion_tokens":10},
        text="hello",
    )
    assert speed.ttft_ms == 250
    assert speed.output_tokens == 10
    assert speed.tokens_per_second == pytest.approx(10 / 1.25)


def test_stream_closed_before_any_token_has_no_speed():
    speed = measure_lines([], started_at=0.0, ended_at=0.2)
    assert speed.ttft_ms is None
    assert speed.tokens_per_second is None
    assert speed.error
