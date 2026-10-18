import base64
import pytest
from studio.engines.images import decode_image, generate_image
from studio.engines.openai_compatible import EngineError
from studio.assets import IMAGE_PATH


def test_valid_png_is_preserved():
    raw = IMAGE_PATH.read_bytes()
    assert decode_image({'data': [{'b64_json': base64.b64encode(raw).decode()}]}) == (raw, 'png')


@pytest.mark.parametrize('payload', [
    {'data': [{'url': 'https://example.com/image.png'}]},
    {'data': [{'b64_json': 'invalid base64!'}]},
    {'data': [{'b64_json': base64.b64encode(b'<svg onload="bad()"></svg>').decode()}]},
    {'data': []},
])
def test_image_response_must_contain_inline_raster_data(payload):
    with pytest.raises(EngineError):
        decode_image(payload)


def test_url_only_response_is_not_downloaded(tmp_path, engine):
    state, base = engine
    state.image_payload = {'data': [{'url': 'https://example.com/never-fetch.png'}]}
    result = generate_image({'base_url': base}, 'test-image', 'test', tmp_path)
    assert 'not downloaded' in result['error']
    assert result['image_path'] is None
    assert list(tmp_path.iterdir()) == []
