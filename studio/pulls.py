"""Server-owned downloads, independent of browser request lifetimes."""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from studio.engines.ollama import iter_pull


class PullManager:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS model_pull (endpoint_id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
            for endpoint_id, payload in conn.execute("SELECT endpoint_id, payload FROM model_pull").fetchall():
                job = json.loads(payload)
                if job["state"] == "running":
                    job.update(state="error", error="Studio restarted during this download. Pull again to resume with Ollama.")
                    conn.execute("UPDATE model_pull SET payload=? WHERE endpoint_id=?", (json.dumps(job), endpoint_id))

    def get(self, endpoint_id):
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT payload FROM model_pull WHERE endpoint_id=?", (endpoint_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _save(self, job):
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT OR REPLACE INTO model_pull VALUES (?, ?)", (job["endpoint_id"], json.dumps(job)))

    def start(self, endpoint, name):
        with self.lock:
            current = self.get(endpoint["id"])
            if current and current["state"] == "running":
                if current["name"] != name:
                    raise ValueError("A model is already downloading on this server. Wait for it to finish.")
                return current
            job = dict(id=uuid.uuid4().hex, endpoint_id=endpoint["id"], name=name,
                       state="running", status="Starting download", completed=None, total=None,
                       error=None, started_at=datetime.now(timezone.utc).isoformat())
            self._save(job)
            threading.Thread(target=self._run, args=(endpoint, job.copy()), daemon=True).start()
            return job

    def _run(self, endpoint, job):
        try:
            succeeded = False
            for event in iter_pull(endpoint["base_url"], job["name"], endpoint.get("api_key")):
                if event.get("error"):
                    raise RuntimeError(event["error"])
                job.update(event)
                succeeded = event.get("status") == "success"
                self._save(job)
            if not succeeded:
                raise RuntimeError("The download connection ended before Ollama confirmed success. Pull again to resume.")
            job.update(state="done", status="Download complete")
        except Exception as exc:
            job.update(state="error", error=str(exc), status="Download failed")
        self._save(job)
