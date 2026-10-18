from studio.engines.openai_compatible import ThinkSplitter, delta_thinking


def test_think_tags_split_across_chunks():
    splitter = ThinkSplitter()
    first = splitter.feed("Answer: <thi")
    second = splitter.feed("nk>two plus two</think>4")
    tail = splitter.finish()
    pieces = first + second + tail
    assert pieces == [("content", "Answer: "), ("thinking", "two plus two"), ("content", "4")]


def test_reasoning_field_is_separate_from_content():
    payload = {"choices": [{"delta": {"reasoning_content": "draft", "content": ""}}]}
    assert delta_thinking(payload) == "draft"
