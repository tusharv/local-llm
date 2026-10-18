import sqlite3
from studio.db import init_db, connect, create_benchmark_run, add_benchmark_result, get_benchmark_run


def test_legacy_results_survive_schema_upgrade(tmp_path):
    path = tmp_path / 'studio.db'
    # Start with exactly the old result constraint and columns, plus one saved result.
    with sqlite3.connect(path) as conn:
        conn.executescript('''
        CREATE TABLE benchmark_run (
          id INTEGER PRIMARY KEY, endpoint_id INTEGER NOT NULL, endpoint_kind TEXT NOT NULL,
          model TEXT NOT NULL, suite_version TEXT NOT NULL, warmup INTEGER NOT NULL,
          repeat_count INTEGER NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT);
        INSERT INTO benchmark_run VALUES(1, 1, 'openai', 'old-model', '1', 0, 1, 'done', '2026-10-18', '2026-10-18');
        CREATE TABLE benchmark_result (
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL,
          case_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('text', 'vision')),
          repeat_index INTEGER NOT NULL, ttft_ms INTEGER, prompt_tokens INTEGER,
          output_tokens INTEGER, tokens_per_second REAL, total_ms INTEGER,
          output_preview TEXT, error TEXT);
        INSERT INTO benchmark_result VALUES(7, 1, 'short', 'text', 0, 12, 3, 2, 5, 400, 'Hello', NULL);
        ''')
    init_db(path)
    init_db(path)  # A second startup must be safe.
    with connect(path) as conn:
        old = dict(conn.execute('SELECT * FROM benchmark_result WHERE id = 7').fetchone())
        assert old['output_preview'] == 'Hello'
        assert old['ttft_ms'] == 12
        assert old['output_text'] is None
        run = create_benchmark_run(conn, endpoint_id=1, endpoint_kind='openai', model='demo', suite_version='2', warmup=False, repeat_count=1, profile='image')
        add_benchmark_result(conn, run_id=run['id'], row={'case_id': 'image_scene', 'kind': 'image', 'repeat_index': 0, 'image_path': 'sample.png'})
        assert get_benchmark_run(conn, run['id'])['profile'] == 'image'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
