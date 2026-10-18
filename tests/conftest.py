import pytest

from tests.support.engine import EngineState, start_engine


@pytest.fixture
def engine():
    state = EngineState()
    base, server = start_engine(state)
    yield state, base
    server.shutdown()
    server.server_close()
