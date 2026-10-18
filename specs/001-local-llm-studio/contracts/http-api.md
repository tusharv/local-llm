# HTTP Contract: Local LLM Studio

Studio's own API, bound to `127.0.0.1:8000`. The engine API is the OpenAI-compatible server stored on an Endpoint. Studio does not expose that engine except through these routes.

JSON uses UTF-8. Errors use `{ "error": "<message>" }` with a 4xx or 5xx status. Streaming routes use Server-Sent Events.

## Endpoints

### `GET /api/endpoints`

Returns the saved endpoints. `api_key` is omitted. Each item includes `id`, `name`, `base_url`, `kind`, `private_network_confirmed`.

### `POST /api/endpoints`

Body: `name`, `base_url`, `kind` (`openai` or `ollama`), optional `api_key`, optional `private_network_confirmed` (boolean).

- Normalize `base_url` so it ends with `/v1`.
- `400` when the host is a public cloud host.
- `400` when the host is a private-network address and `private_network_confirmed` is not true.
- `201` with the saved endpoint otherwise.

### `DELETE /api/endpoints/{id}`

Deletes the endpoint row. Conversations that pointed at it remain, with sends failing until the person picks another endpoint. `404` when missing.

### `GET /api/health?endpoint_id={id}`

Asks that endpoint for `GET {base}/v1/models` with a short timeout.

- `200` `{ "ok": true, "model_count": <n> }` when the server answers.
- `200` `{ "ok": false, "error": "<message>" }` when it does not. This is not a Studio crash.

### `GET /api/models?endpoint_id={id}`

Lists model ids from `GET {base}/v1/models`. For kind `ollama`, also reads native details when the native port is the same host on `11434` or the `/v1` URL's origin.

Each item: `id`, `vision` (boolean, effective flag), `vision_source` (`override`, `capabilities`, `family`, `probe`, or `unknown`), optional `size_bytes` and `family` for Ollama.

### `POST /api/models/pull`

Body: `endpoint_id`, `name`. SSE progress events `{ "status": "<text>", "completed": <n|null>, "total": <n|null> }`, then a done event. `400` when the endpoint kind is not `ollama`.

### `DELETE /api/models/{model_name}?endpoint_id={id}`

Deletes the model on an Ollama endpoint. `400` when kind is not `ollama`. `model_name` may contain `:` and `/` and is passed through as one path segment.

### `PUT /api/models/flags`

Body: `endpoint_id`, `model`, `vision_override` (`on`, `off`, or null). Upserts ModelFlag. Returns the effective vision boolean.

### `GET /api/conversations`

Returns conversation summaries: `id`, `title`, `endpoint_id`, `model`, `updated_at`.

### `POST /api/conversations`

Body: `endpoint_id`, `model`, optional `title`. `201` with the conversation.

### `GET /api/conversations/{id}`

Returns the conversation and its messages in order. Image messages include a local URL under `/uploads/...`, not a remote URL.

### `DELETE /api/conversations/{id}`

Deletes messages, the conversation, and any image files those messages referenced.

### `POST /api/chat`

Body: `conversation_id`, `content`, optional multipart image when the model is vision-flagged. SSE events:

- `{ "delta": "<text>" }` for assistant text
- `{ "done": true, "message_id": <id> }` when stored
- `{ "error": "<message>" }` when the engine fails

A text-only model with an image is `400` before any engine call.

### `POST /api/vision-check`

Body: `endpoint_id`, `model`. Runs the bundled image and the fixed question. Response JSON: `answer`, `ttft_ms`, `total_ms`, `vision` (boolean). A model that rejects the image updates the probe to `text` and returns `vision: false` with an explanation in `answer`.

### `POST /api/benchmarks`

Body: `endpoint_id`, `model`, `warmup` (boolean, default true), `repeat_count` (1 or 3). `409` when another run is `running`. SSE events name the case id and repeat index, then a final `{ "run_id": <id>, "status": "done" }`.

### `GET /api/benchmarks`

Returns runs, newest first, including endpoint name, model, suite version, and status.

### `GET /api/benchmarks/{id}`

Returns the run and its result rows.

### `GET /api/benchmarks/{id}/export`

Returns the same payload as `application/json` with a download filename.

## Engine calls Studio makes

- `GET {base}/v1/models`
- `POST {base}/v1/chat/completions` with `stream: true`. Image parts use `image_url` data URLs. Request `stream_options.include_usage` when the server supports it. Ignore a refusal and still parse deltas.
- Ollama only, on the origin of the base URL: `POST /api/show`, `POST /api/pull` (stream), `DELETE /api/delete`.

## Upload URL

`GET /uploads/{filename}` serves a file from `./data/uploads` only. Paths that escape that directory are `404`.

## Benchmark report extension (suite v2, 2026-10-19)

`POST /api/benchmarks` also accepts `profile`: `standard` (default), `code`, or `image`. Unknown profiles return 422. Image runs use the saved endpoint's `/v1/images/generations` route with model, fixed prompt, `n: 1`, `size: "512x512"`, and `response_format: "b64_json"`.

Progress events include `event`: `plan` (run id, case metadata, total), `warmup`, `warmup_complete`, `case_started`, `case_complete` (completed and total counts), `error`, and `finished`. Case failures are preserved and set final run status to `error`; unexpected/warmup errors are also saved on the run.

Run records add `profile`, `expected_results`, and `error`. Result records add `output_text` (up to 32,000 characters), `token_basis` (`tokens`, `chunks`, or unknown), and `image_url` (local upload URL, or null). Kinds now include `code` and `image`.

List responses attach a `summary` to each run. Detail and export responses return `{run, results, summary}`. Summary contains successful/failed/planned counts, median timing, per-case medians, measured duration, token basis, and a comparison key. A null comparison key means the run is incomplete or failed. Medians exclude failed samples. These are performance measurements, not quality scores.
