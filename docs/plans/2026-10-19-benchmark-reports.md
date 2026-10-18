# Benchmark reports implementation

Approved direction: visual reports, code generation, optional local image generation, live progress, and comparable saved runs.

- [x] Extend suite v2 with standard, code, and image profiles. Save the profile, full bounded output, image path, and token-count basis. Migrate old databases without losing results.
- [x] Add an OpenAI-compatible local image client requesting base64 output; accept bounded PNG/JPEG/WebP data only, never fetch response URLs. Measure full request time and report unsupported endpoints as failures.
- [x] Emit planned, started, completed, and final events. Failed cases must mark the run failed while preserving successful cases.
- [x] Create server-side summaries: medians of successful cases, completion fraction, per-case metrics, and a comparison key incorporating suite, profile, cases, repetitions, warmup, and timing basis.
- [x] Rebuild the benchmark UI with profile controls, progress, report metrics, per-case charts, output previews, compatible-run comparison, JSON export, and print-to-PDF layout.
- [x] Test migrations, timing aggregation, image validation, unsupported image responses, code output storage, partial failure, progress, browser interactions, responsive layout, and printing.

Images use a saved local/private endpoint's /v1/images/generations route and a user-selected model. No cloud provider is added. Image generation is optional and uses separate runs. Quality scoring and code execution are outside this change. Images are stored in data/uploads under generated filenames. Legacy v1 remains readable but cannot be compared with v2.
