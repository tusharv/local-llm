import uuid
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS endpoint (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('openai', 'ollama')),
    api_key TEXT,
    private_network_confirmed INTEGER NOT NULL DEFAULT 0 CHECK (private_network_confirmed IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation (
    id INTEGER PRIMARY KEY,
    endpoint_id INTEGER NOT NULL,
    model TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    image_path TEXT,
    error TEXT,
    thinking TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_flag (
    endpoint_id INTEGER NOT NULL,
    model TEXT NOT NULL,
    vision_override TEXT CHECK (vision_override IN ('on', 'off')),
    probe_result TEXT CHECK (probe_result IN ('vision', 'text')),
    probed_at TEXT,
    PRIMARY KEY (endpoint_id, model)
);

CREATE TABLE IF NOT EXISTS benchmark_run (
    id INTEGER PRIMARY KEY,
    endpoint_id INTEGER NOT NULL,
    endpoint_kind TEXT NOT NULL,
    model TEXT NOT NULL,
    suite_version TEXT NOT NULL,
    warmup INTEGER NOT NULL CHECK (warmup IN (0, 1)),
    repeat_count INTEGER NOT NULL CHECK (repeat_count IN (1, 3)),
    status TEXT NOT NULL CHECK (status IN ('running', 'done', 'error')),
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS benchmark_result (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES benchmark_run(id) ON DELETE CASCADE,
    case_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('text', 'vision', 'code', 'image')),
    repeat_index INTEGER NOT NULL,
    ttft_ms INTEGER,
    prompt_tokens INTEGER,
    output_tokens INTEGER,
    tokens_per_second REAL,
    total_ms INTEGER,
    output_preview TEXT,
    output_text TEXT,
    image_path TEXT,
    token_basis TEXT,
    error TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        if "public_id" not in {row[1] for row in conn.execute("PRAGMA table_info(conversation)")}:
            conn.execute("ALTER TABLE conversation ADD COLUMN public_id TEXT")
        for row in conn.execute("SELECT id FROM conversation WHERE public_id IS NULL").fetchall():
            conn.execute("UPDATE conversation SET public_id=? WHERE id=?", (uuid.uuid4().hex, row[0]))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS conversation_public_id ON conversation(public_id)")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(message)")}
        if "thinking" not in columns:
            conn.execute("ALTER TABLE message ADD COLUMN thinking TEXT")
        run_columns = {row[1] for row in conn.execute("PRAGMA table_info(benchmark_run)")}
        for name, definition in {"profile": "TEXT NOT NULL DEFAULT 'standard'", "expected_results": "INTEGER NOT NULL DEFAULT 0", "error": "TEXT"}.items():
            if name not in run_columns:
                conn.execute(f"ALTER TABLE benchmark_run ADD COLUMN {name} {definition}")
        result_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'benchmark_result'").fetchone()[0]
        if "'code'" not in result_sql:
            # Rebuild the CHECK constraint transactionally, retaining IDs and every legacy row.
            definition = SCHEMA[SCHEMA.index("CREATE TABLE IF NOT EXISTS benchmark_result"):]
            conn.execute(definition.replace("benchmark_result (", "benchmark_result_new (", 1))
            columns = [row[1] for row in conn.execute("PRAGMA table_info(benchmark_result)")]
            names = ", ".join(columns)
            conn.execute(f"INSERT INTO benchmark_result_new ({names}) SELECT {names} FROM benchmark_result")
            conn.execute("DROP TABLE benchmark_result")
            conn.execute("ALTER TABLE benchmark_result_new RENAME TO benchmark_result")



@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def public_endpoint(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "base_url": row["base_url"],
        "kind": row["kind"],
        "private_network_confirmed": bool(row["private_network_confirmed"]),
    }


def create_endpoint(
    conn: sqlite3.Connection,
    *,
    name: str,
    base_url: str,
    kind: str,
    api_key: str | None,
    private_network_confirmed: bool,
) -> dict:
    cur = conn.execute(
        """
        INSERT INTO endpoint (name, base_url, kind, api_key, private_network_confirmed, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, base_url, kind, api_key, 1 if private_network_confirmed else 0, now_iso()),
    )
    return get_endpoint(conn, int(cur.lastrowid)) or {}


def list_endpoints(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM endpoint ORDER BY id").fetchall()
    return [public_endpoint(dict(row)) for row in rows]


def get_endpoint(conn: sqlite3.Connection, endpoint_id: int) -> dict | None:
    return _row(conn.execute("SELECT * FROM endpoint WHERE id = ?", (endpoint_id,)).fetchone())


def delete_endpoint(conn: sqlite3.Connection, endpoint_id: int) -> bool:
    cur = conn.execute("DELETE FROM endpoint WHERE id = ?", (endpoint_id,))
    return cur.rowcount > 0


def create_conversation(
    conn: sqlite3.Connection, *, endpoint_id: int, model: str, title: str
) -> dict:
    now = now_iso()
    cur = conn.execute(
        """
        INSERT INTO conversation (endpoint_id, model, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (endpoint_id, model, title, now, now),
    )
    conn.execute("UPDATE conversation SET public_id=? WHERE id=?", (uuid.uuid4().hex, cur.lastrowid))
    return get_conversation(conn, int(cur.lastrowid)) or {}


def list_conversations(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, public_id, title, endpoint_id, model, updated_at
        FROM conversation
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conn: sqlite3.Connection, conversation_id: int) -> dict | None:
    row = _row(conn.execute("SELECT * FROM conversation WHERE id = ?", (conversation_id,)).fetchone())
    if row is None:
        return None
    messages = conn.execute(
        "SELECT * FROM message WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    row["messages"] = [dict(message) for message in messages]
    return row


def touch_conversation(conn: sqlite3.Connection, conversation_id: int, title: str | None = None) -> None:
    if title is None:
        conn.execute(
            "UPDATE conversation SET updated_at = ? WHERE id = ?",
            (now_iso(), conversation_id),
        )
        return
    conn.execute(
        "UPDATE conversation SET updated_at = ?, title = ? WHERE id = ?",
        (now_iso(), title, conversation_id),
    )


def delete_conversation(conn: sqlite3.Connection, conversation_id: int) -> list[str] | None:
    exists = conn.execute("SELECT id FROM conversation WHERE id = ?", (conversation_id,)).fetchone()
    if exists is None:
        return None
    rows = conn.execute(
        """
        SELECT image_path FROM message
        WHERE conversation_id = ? AND image_path IS NOT NULL
        """,
        (conversation_id,),
    ).fetchall()
    paths = [row["image_path"] for row in rows if row["image_path"]]
    conn.execute("DELETE FROM conversation WHERE id = ?", (conversation_id,))
    return paths


def add_message(
    conn: sqlite3.Connection,
    *,
    conversation_id: int,
    role: str,
    content: str,
    image_path: str | None = None,
    error: str | None = None,
    thinking: str | None = None,
) -> dict:
    cur = conn.execute(
        """
        INSERT INTO message (conversation_id, role, content, image_path, error, thinking, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, role, content, image_path, error, thinking, now_iso()),
    )
    row = conn.execute("SELECT * FROM message WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row) if row else {}


def get_model_flag(conn: sqlite3.Connection, endpoint_id: int, model: str) -> dict | None:
    return _row(
        conn.execute(
            "SELECT * FROM model_flag WHERE endpoint_id = ? AND model = ?",
            (endpoint_id, model),
        ).fetchone()
    )


def set_vision_override(
    conn: sqlite3.Connection, *, endpoint_id: int, model: str, vision_override: str | None
) -> dict:
    existing = get_model_flag(conn, endpoint_id, model)
    if existing is None:
        conn.execute(
            """
            INSERT INTO model_flag (endpoint_id, model, vision_override, probe_result, probed_at)
            VALUES (?, ?, ?, NULL, NULL)
            """,
            (endpoint_id, model, vision_override),
        )
    else:
        conn.execute(
            "UPDATE model_flag SET vision_override = ? WHERE endpoint_id = ? AND model = ?",
            (vision_override, endpoint_id, model),
        )
    return get_model_flag(conn, endpoint_id, model) or {}


def set_probe_result(
    conn: sqlite3.Connection, *, endpoint_id: int, model: str, probe_result: str
) -> dict:
    now = now_iso()
    existing = get_model_flag(conn, endpoint_id, model)
    if existing is None:
        conn.execute(
            """
            INSERT INTO model_flag (endpoint_id, model, vision_override, probe_result, probed_at)
            VALUES (?, ?, NULL, ?, ?)
            """,
            (endpoint_id, model, probe_result, now),
        )
    else:
        conn.execute(
            """
            UPDATE model_flag SET probe_result = ?, probed_at = ?
            WHERE endpoint_id = ? AND model = ?
            """,
            (probe_result, now, endpoint_id, model),
        )
    return get_model_flag(conn, endpoint_id, model) or {}


def has_running_benchmark(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM benchmark_run WHERE status = 'running' LIMIT 1"
    ).fetchone()
    return row is not None


def create_benchmark_run(
    conn: sqlite3.Connection,
    *,
    endpoint_id: int,
    endpoint_kind: str,
    model: str,
    suite_version: str,
    warmup: bool,
    repeat_count: int,
    status: str = "running",
    profile: str = "standard",
) -> dict:
    now = now_iso()
    cur = conn.execute(
        """
        INSERT INTO benchmark_run (
            endpoint_id, endpoint_kind, model, suite_version, warmup, repeat_count,
            status, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            endpoint_id,
            endpoint_kind,
            model,
            suite_version,
            1 if warmup else 0,
            repeat_count,
            status,
            now,
        ),
    )
    conn.execute("UPDATE benchmark_run SET profile = ? WHERE id = ?", (profile, cur.lastrowid))
    return get_benchmark_run(conn, int(cur.lastrowid)) or {}


def finish_benchmark_run(conn: sqlite3.Connection, run_id: int, status: str) -> None:
    conn.execute(
        "UPDATE benchmark_run SET status = ?, finished_at = ? WHERE id = ?",
        (status, now_iso(), run_id),
    )


def add_benchmark_result(conn: sqlite3.Connection, *, run_id: int, row: dict) -> dict:
    cur = conn.execute(
        """
        INSERT INTO benchmark_result (
            run_id, case_id, kind, repeat_index, ttft_ms, prompt_tokens, output_tokens,
            tokens_per_second, total_ms, output_preview, error, output_text, image_path, token_basis
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            row["case_id"],
            row["kind"],
            row["repeat_index"],
            row.get("ttft_ms"),
            row.get("prompt_tokens"),
            row.get("output_tokens"),
            row.get("tokens_per_second"),
            row.get("total_ms"),
            row.get("output_preview"),
            row.get("error"),
            row.get("output_text"),
            row.get("image_path"),
            row.get("token_basis"),
        ),
    )
    stored = conn.execute("SELECT * FROM benchmark_result WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(stored) if stored else {}


def list_benchmark_runs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT r.*, e.name AS endpoint_name
        FROM benchmark_run r
        LEFT JOIN endpoint e ON e.id = r.endpoint_id
        ORDER BY r.id DESC
        """
    ).fetchall()
    return [_public_run(dict(row)) for row in rows]


def get_benchmark_run(conn: sqlite3.Connection, run_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT r.*, e.name AS endpoint_name
        FROM benchmark_run r
        LEFT JOIN endpoint e ON e.id = r.endpoint_id
        WHERE r.id = ?
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    run = _public_run(dict(row))
    results = conn.execute(
        "SELECT * FROM benchmark_result WHERE run_id = ? ORDER BY id",
        (run_id,),
    ).fetchall()
    run["results"] = [dict(result) for result in results]
    return run


def _public_run(row: dict) -> dict:
    return {
        "id": row["id"],
        "endpoint_id": row["endpoint_id"],
        "endpoint_name": row.get("endpoint_name"),
        "endpoint_kind": row["endpoint_kind"],
        "model": row["model"],
        "suite_version": row["suite_version"],
        "warmup": bool(row["warmup"]),
        "repeat_count": row["repeat_count"],
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "profile": row.get("profile", "standard"),
        "expected_results": row.get("expected_results", 0),
        "error": row.get("error"),
    }
