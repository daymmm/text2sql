"""
validator.py
------------
Security layer that sits between SQL generation and execution.

WHAT IT DOES:
  - Blocks any query that is NOT a pure SELECT statement
  - Catches DML: INSERT, UPDATE, DELETE
  - Catches DDL: DROP, ALTER, CREATE, TRUNCATE
  - Catches privilege commands: GRANT, REVOKE
  - Catches comment-based injection attempts (-- and /* */)

WHY THIS MATTERS:
  An LLM might generate "SELECT ... ; DROP TABLE customers" by accident
  (or by a malicious user prompt). This validator catches it before
  the query ever reaches the database.

USAGE:
  safe, reason = is_safe_query(sql)
  if not safe:
      return error to user
"""

import re


# Keywords that must never appear in an allowed query
BLOCKED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP",
    "ALTER",  "CREATE", "TRUNCATE", "GRANT",
    "REVOKE", "EXECUTE", "EXEC", "CALL",
    "COPY",   "VACUUM",  "REINDEX",
]


def is_safe_query(sql: str) -> tuple[bool, str]:
    """
    Validates that sql is a safe, read-only SELECT query.

    Returns:
        (True,  "OK")           → safe to execute
        (False, "reason")       → blocked, with reason string
    """
    if not sql or not sql.strip():
        return False, "Empty query"

    # Strip leading/trailing whitespace and normalise
    cleaned = sql.strip()

    # ── Rule 1: Must start with SELECT ────────────────────────
    if not cleaned.upper().lstrip().startswith("SELECT"):
        return False, f"Query must start with SELECT. Got: {cleaned[:30]}..."

    # ── Rule 2: Block dangerous keywords ──────────────────────
    # We use word-boundary regex so we don't block e.g. "CREATED_AT"
    upper = cleaned.upper()
    for keyword in BLOCKED_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, upper):
            return False, f"Blocked keyword detected: '{keyword}'"

    # ── Rule 3: Block stacked queries (semicolon mid-query) ───
    # Allow ONE trailing semicolon only
    body = cleaned.rstrip(";").rstrip()
    if ";" in body:
        return False, "Multiple statements detected (semicolon in query body)"

    # ── Rule 4: Block SQL comment injection ───────────────────
    if "--" in cleaned:
        return False, "SQL comment injection detected (--)"
    if "/*" in cleaned:
        return False, "SQL block comment injection detected (/*)"

    return True, "OK"


def sanitise_sql(sql: str) -> str:
    """
    Light cleanup of LLM output before validation:
      - Strip markdown code fences
      - Strip leading/trailing whitespace
    """
    sql = sql.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    sql = sql.strip()
    return sql