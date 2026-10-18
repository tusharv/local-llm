import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class EngineState:
    def __init__(self) -> None:
        self.models = ["demo-text"]
        self.chunks = ["Hello"]
        self.reasoning_chunks: list[str] = []
        self.usage = {"prompt_tokens": 3, "completion_tokens": 2}
        self.first_byte_delay = 0
        self.chat_requests: list[dict] = []
        self.chat_error: str | None = None
        self.show_by_name: dict[str, dict] = {}
        self.show_calls: list[str] = []
        self.pulls: list[str] = []
        self.deleted: list[str] = []


def start_engine(state: EngineState) -> tuple[str, ThreadingHTTPServer]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path.rstrip("/").endswith("/models"):
                self._json(200, {"object": "list", "data": [{"id": model} for model in state.models]})
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            body = self._body()
            if path.endswith("/chat/completions"):
                state.chat_requests.append(body)
                if state.chat_error:
                    self._json(400, {"error": {"message": state.chat_error}})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                if state.first_byte_delay:
                    time.sleep(state.first_byte_delay)
                for chunk in state.reasoning_chunks:
                    payload = {"choices": [{"delta": {"reasoning_content": chunk}}]}
                    self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                    self.wfile.flush()
                for chunk in state.chunks:
                    payload = {"choices": [{"delta": {"content": chunk}}]}
                    self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                    self.wfile.flush()
                if state.usage is not None:
                    usage_payload = {"choices": [{"delta": {}}], "usage": state.usage}
                    self.wfile.write(f"data: {json.dumps(usage_payload)}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                return
            if path.endswith("/api/show"):
                name = str(body.get("name") or body.get("model") or "")
                state.show_calls.append(name)
                self._json(200, state.show_by_name.get(name, {}))
                return
            if path.endswith("/api/pull"):
                state.pulls.append(str(body.get("name") or ""))
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                self.wfile.write(b'{"status":"pulling","completed":1,"total":2}\n')
                self.wfile.write(b'{"status":"success","completed":2,"total":2}\n')
                return
            self._json(404, {"error": "not found"})

        def do_DELETE(self) -> None:
            path = self.path.split("?", 1)[0]
            body = self._body()
            if path.endswith("/api/delete"):
                state.deleted.append(str(body.get("name") or ""))
                self._json(200, {"ok": True})
                return
            self._json(404, {"error": "not found"})

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            return json.loads(raw.decode())

        def _json(self, status: int, payload: dict) -> None:
            raw = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return f"http://{host}:{port}/v1", server
