from studio.assets import QUESTION

SUITE_VERSION = "2"

CASES = (
    {"id": "short", "kind": "text", "title": "Quick response", "prompt": "Reply with one word: hello."},
    {"id": "longer", "kind": "text", "title": "Explanation", "prompt": "Explain in two short sentences what a local language model is."},
    {"id": "reason", "kind": "text", "title": "Reasoning", "prompt": "What is 17 + 28? Show one line of arithmetic, then the result."},
    {"id": "code_python", "kind": "code", "title": "Python generation", "prompt": "Write a Python function unique_in_order(items) that removes duplicates while preserving order. Include a docstring and three assert examples. Return only a fenced Python code block, under 40 lines."},
    {"id": "code_javascript", "kind": "code", "title": "JavaScript generation", "prompt": "Write a JavaScript function groupBy(items, key) that groups an array of objects by a property. Include an example and handle a missing property. Return only a fenced JavaScript code block, under 40 lines."},
    {"id": "vision", "kind": "vision", "title": "Image understanding", "prompt": QUESTION},
    {"id": "image_scene", "kind": "image", "title": "Image generation", "prompt": "A red ceramic mug beside a closed blue notebook on a pale wooden desk, soft morning daylight, clean product photograph, no text, square composition."},
)


def cases_for(*, vision: bool, profile: str = "standard") -> list[dict]:
    if profile == "image":
        kinds = {"image"}
    elif profile == "code":
        kinds = {"code"}
    else:
        kinds = {"text", "code"} | ({"vision"} if vision else set())
    return [dict(case) for case in CASES if case["kind"] in kinds]
