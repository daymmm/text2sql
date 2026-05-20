"""
executor.py
-----------
The orchestrator — runs the full pipeline end-to-end.

PIPELINE FLOW:
  1. decompose_question()    → structured JSON
  2. generate_sql()          → SQL string
  3. is_safe_query()         → security check
  4. execute_query()         → run on PostgreSQL
  5. [if error] fix_sql()    → repair query
  6. [retry] execute_query() → run fixed SQL
  7. log_query()             → write to logs/query_logs.json
  8. return structured output dict

RETRY POLICY (Task 3 requirement):
  Maximum 1 retry. If the fixed query also fails, the pipeline
  reports the final error without crashing.

LOGGING:
  Every execution — success or failure — is appended to
  logs/query_logs.json as a structured JSON entry.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from database import execute_query
from sql_generator import decompose_question, generate_sql, fix_sql
from validator import is_safe_query, sanitise_sql

LOG_FILE = Path("logs/query_logs.json")


# ── LOGGING ───────────────────────────────────────────────────
def _load_logs() -> list:
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def log_query(entry: dict):
    """Appends one log entry to logs/query_logs.json."""
    logs = _load_logs()
    logs.append(entry)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)


# ── RESULT FORMATTER ──────────────────────────────────────────
def _format_rows(columns: list, rows: list) -> list[dict]:
    """Turns raw tuple rows into a list of column→value dicts."""
    return [dict(zip(columns, row)) for row in rows]


# ── MAIN PIPELINE ─────────────────────────────────────────────
def run_pipeline(question: str) -> dict:
    """
    Runs the complete Text-to-SQL pipeline for one question.

    Returns:
    {
      "question":       "...",
      "decomposition":  {...},
      "sql":            "SELECT ...",
      "result":         [{...}, ...],
      "rowcount":       5,
      "status":         "success" | "failed" | "blocked",
      "retry":          False | True,
      "error":          None | "error string",
      "latency_ms":     142
    }
    """
    start_time = time.time()

    log_entry = {
        "timestamp":     datetime.now().isoformat(),
        "question":      question,
        "decomposition": None,
        "sql_original":  None,
        "sql_final":     None,
        "retry":         False,
        "status":        None,
        "error":         None,
        "rowcount":      0,
        "latency_ms":    None,
    }

    output = {
        "question":      question,
        "decomposition": None,
        "sql":           None,
        "result":        [],
        "rowcount":      0,
        "status":        "failed",
        "retry":         False,
        "error":         None,
        "latency_ms":    0,
    }

    try:
        # ── STEP 1: DECOMPOSE ─────────────────────────────────
        decomposition = decompose_question(question)
        log_entry["decomposition"] = decomposition
        output["decomposition"]    = decomposition

        # ── STEP 2: GENERATE SQL ──────────────────────────────
        sql = generate_sql(decomposition, question)
        sql = sanitise_sql(sql)
        log_entry["sql_original"] = sql
        output["sql"]             = sql

        # ── STEP 3: VALIDATE (security check) ─────────────────
        safe, reason = is_safe_query(sql)
        if not safe:
            log_entry["status"] = "blocked"
            log_entry["error"]  = reason
            output["status"]    = "blocked"
            output["error"]     = reason
            _finalise(log_entry, output, start_time)
            log_query(log_entry)
            return output

        # ── STEP 4: EXECUTE ───────────────────────────────────
        result = execute_query(sql)

        # ── STEP 5 & 6: RETRY if failed ───────────────────────
        if result["error"]:
            log_entry["retry"] = True
            output["retry"]    = True

            # Ask Claude to fix the broken SQL
            fixed_sql = fix_sql(sql, result["error"], question)
            fixed_sql = sanitise_sql(fixed_sql)
            log_entry["sql_fixed"] = fixed_sql

            # Validate the fixed query too
            safe2, reason2 = is_safe_query(fixed_sql)
            if safe2:
                result = execute_query(fixed_sql)
                sql    = fixed_sql          # use fixed version as final
                output["sql"] = fixed_sql
            else:
                result["error"] = f"Fixed query also blocked: {reason2}"

        # ── STEP 7: BUILD OUTPUT ──────────────────────────────
        log_entry["sql_final"] = sql
        log_entry["rowcount"]  = result["rowcount"]

        if result["error"]:
            log_entry["status"] = "failed"
            log_entry["error"]  = result["error"]
            output["status"]    = "failed"
            output["error"]     = result["error"]
        else:
            log_entry["status"] = "success"
            output["status"]    = "success"
            output["result"]    = _format_rows(result["columns"], result["rows"])
            output["rowcount"]  = result["rowcount"]

    except Exception as e:
        # Catch-all — pipeline must never crash
        log_entry["status"] = "error"
        log_entry["error"]  = str(e)
        output["status"]    = "error"
        output["error"]     = str(e)

    _finalise(log_entry, output, start_time)
    log_query(log_entry)
    return output


def _finalise(log_entry: dict, output: dict, start_time: float):
    """Stamps latency into both the log entry and output dict."""
    ms = round((time.time() - start_time) * 1000)
    log_entry["latency_ms"] = ms
    output["latency_ms"]    = ms