# Data Model: Local LLM Studio

Database file: `./data/studio.db`. Images: `./data/uploads/`. Both are created at startup and gitignored.

## Endpoint

A local server the person saved.

- `id`: integer, primary key
- `name`: text, required
- `base_url`: text, required, normalized to end with `/v1`
- `kind`: text, `openai` or `ollama`
- `api_key`: text, nullable, used only as a bearer token to that local server
- `private_network_confirmed`: integer, 0 or 1
- `created_at`: text, ISO-8601

Loopback URLs store `private_network_confirmed` as 0. Private-network URLs store 1 only after confirm. Public cloud URLs are never inserted.

## Conversation

- `id`: integer, primary key
- `endpoint_id`: integer, foreign key to Endpoint, required
- `model`: text, required, the model id on that endpoint
- `title`: text, required
- `created_at`: text
- `updated_at`: text

Deleting a conversation deletes its messages and their image files.

## Message

- `id`: integer, primary key
- `conversation_id`: integer, foreign key, required
- `role`: text, `user` or `assistant`
- `content`: text, required, may be empty when an error is stored instead
- `image_path`: text, nullable, path relative to `./data`
- `error`: text, nullable
- `created_at`: text

## ModelFlag

One row per endpoint and model id.

- `endpoint_id`: integer, foreign key
- `model`: text
- `vision_override`: text, nullable, `on`, `off`, or null when the person has not chosen
- `probe_result`: text, nullable, `vision`, `text`, or null
- `probed_at`: text, nullable

Effective vision is the override when set. Otherwise a native capability or known family name. Otherwise the cached probe.

## BenchmarkRun

- `id`: integer, primary key
- `endpoint_id`: integer, foreign key
- `endpoint_kind`: text, copied at run time
- `model`: text
- `suite_version`: text, matches the suite constant
- `warmup`: integer, 0 or 1
- `repeat_count`: integer, 1 or 3
- `status`: text, `running`, `done`, or `error`
- `started_at`: text
- `finished_at`: text, nullable

## BenchmarkResult

- `id`: integer, primary key
- `run_id`: integer, foreign key
- `case_id`: text
- `kind`: text, `text` or `vision`
- `repeat_index`: integer
- `ttft_ms`: integer, nullable
- `prompt_tokens`: integer, nullable
- `output_tokens`: integer, nullable
- `tokens_per_second`: real, nullable
- `total_ms`: integer, nullable
- `output_preview`: text, nullable, truncated
- `error`: text, nullable

Runs of different `suite_version` values are not compared on the comparison page.

## Relationships

- An Endpoint has many Conversations, ModelFlags, and BenchmarkRuns.
- A Conversation has many Messages.
- A BenchmarkRun has many BenchmarkResults.

## Onboarding record (file, not a table)

`./data/onboarding.json`, written only when the person finishes the interactive flow.

- `completed_at`: ISO-8601 text
- `os`: `darwin`, `windows`, or `linux`
- `endpoint_id`: integer or null, the endpoint saved from the menu
- `detections`: list of `{ "runtime", "state", "detail" }` where state is `running`, `stopped`, or `missing`

The file being absent means the next interactive `python -m studio` runs onboarding. `--onboard` ignores the file and overwrites it at the end. A non-interactive start does not create the file.

## Suite content (not a table)

`suite_version` is a constant in `studio/benchmarks/suite.py`. v1 cases:

- `short`: one short reply prompt
- `longer`: one explanation prompt
- `reason`: one small reasoning prompt
- `vision`: the bundled image plus one fixed question, included only when the model is vision-flagged
