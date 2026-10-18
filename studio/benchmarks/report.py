"""Descriptive performance measurements, never model quality scores."""
import json
import math
from statistics import median

from studio.benchmarks.suite import CASES

LABELS = {case["id"]: case["title"] for case in CASES}


def _median(rows: list[dict], key: str):
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float)) and math.isfinite(row[key])]
    return round(median(values), 2) if values else None


def summarize(run: dict, rows: list[dict]) -> dict:
    successful = [row for row in rows if not row.get("error")]
    total = run.get("expected_results") or len(rows)
    cases = []
    for case_id in dict.fromkeys(row["case_id"] for row in rows):
        group = [row for row in rows if row["case_id"] == case_id]
        good = [row for row in group if not row.get("error")]
        cases.append({
            "id": case_id, "title": LABELS.get(case_id, case_id), "kind": group[0]["kind"],
            "completed": len(good), "total": len(group),
            "median_ttft_ms": _median(good, "ttft_ms"),
            "median_total_ms": _median(good, "total_ms"),
            "median_tokens_per_second": _median(good, "tokens_per_second"),
        })
    basis = sorted({row.get("token_basis") or "unknown" for row in successful if row["kind"] != "image"})
    key = None
    if rows and len(successful) == total and not run.get("error") and run.get("status") not in ("error", "running"):
        key = json.dumps([run.get("suite_version"), run.get("profile", "standard"),
                          sorted((case["id"], case["total"]) for case in cases),
                          run.get("warmup"), run.get("repeat_count"), basis], separators=(",", ":"))
    return {
        "completed": len(successful), "total": total, "failed": len(rows) - len(successful),
        "median_ttft_ms": _median(successful, "ttft_ms"),
        "median_tokens_per_second": _median(successful, "tokens_per_second"),
        "median_total_ms": _median(successful, "total_ms"),
        "measured_ms": sum(row.get("total_ms") or 0 for row in rows),
        "token_basis": basis[0] if len(basis) == 1 else "mixed" if basis else "none",
        "cases": cases, "comparison_key": key,
    }
