from studio.assets import QUESTION

SUITE_VERSION = "1"

CASES = (
    {
        "id": "short",
        "kind": "text",
        "prompt": "Reply with one word: hello.",
    },
    {
        "id": "longer",
        "kind": "text",
        "prompt": "Explain in two short sentences what a local language model is.",
    },
    {
        "id": "reason",
        "kind": "text",
        "prompt": "What is 17 + 28? Show one line of arithmetic, then the result.",
    },
    {
        "id": "vision",
        "kind": "vision",
        "prompt": QUESTION,
    },
)


def cases_for(*, vision: bool) -> list[dict]:
    return [dict(case) for case in CASES if case["kind"] == "text" or vision]
