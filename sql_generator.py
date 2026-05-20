"""
sql_generator.py
----------------
The brain of the pipeline. Makes 3 types of LLM calls:

  1. decompose_question(question)
       → Break NL into structured JSON
         (intent, tables, columns, filters, joins, etc.)

  2. generate_sql(decomposition, question)
       → Turn decomposition JSON into SQL

  3. fix_sql(sql, error, question)
       → Fix broken SQL using DB error messages

WHY 3 SEPARATE CALLS?
  This is called "prompt chaining".

  Chain:
      Understand → Generate → Fix

This is more reliable than one giant prompt.

IMPORTANT:
  All 3 functions NEVER raise.
  Errors are returned safely.
"""

import json
import os

from groq import Groq
from dotenv import load_dotenv

from prompts.templates import (
    SCHEMA,
    DECOMPOSE_PROMPT,
    GENERATE_PROMPT,
    FIX_PROMPT
)

from validator import sanitise_sql


# Load .env variables
load_dotenv()


# Shared Groq client
_client = None


def get_client():
    """
    Creates one reusable Groq client instance.
    """

    global _client

    if _client is None:

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY not set in .env")

        _client = Groq(api_key=api_key)

    return _client


def _call_llm(prompt: str, max_tokens: int = 1024) -> str:
    """
    Internal helper:
    Sends prompt to Groq and returns text response.
    """

    client = get_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        max_tokens=max_tokens,
        temperature=0
    )

    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────
# CALL 1: DECOMPOSE QUESTION
# ─────────────────────────────────────────────────────────────

def decompose_question(question: str) -> dict:
    """
    Breaks natural language into structured JSON.

    Example output:

    {
      "intent": "find customers",
      "tables": ["customers"],
      "columns": ["customerName"],
      "filters": [],
      "joins": [],
      "group_by": [],
      "aggregation": "none",
      "order_by": "none",
      "limit": null
    }
    """

    try:

        prompt = DECOMPOSE_PROMPT.format(
            schema=SCHEMA,
            question=question
        )

        raw = _call_llm(prompt, max_tokens=512)

        # Remove accidental markdown formatting
        raw = (
            raw.replace("```json", "")
               .replace("```", "")
               .strip()
        )

        decomp = json.loads(raw)

        return decomp

    except json.JSONDecodeError:

        return {
            "intent": question,
            "tables": [],
            "columns": ["*"],
            "filters": [],
            "joins": [],
            "group_by": [],
            "aggregation": "none",
            "order_by": "none",
            "limit": None,
            "_parse_error": "LLM returned non-JSON decomposition"
        }

    except Exception as e:

        return {
            "intent": question,
            "tables": [],
            "columns": ["*"],
            "filters": [],
            "joins": [],
            "group_by": [],
            "aggregation": "none",
            "order_by": "none",
            "limit": None,
            "_error": str(e)
        }


# ─────────────────────────────────────────────────────────────
# CALL 2: GENERATE SQL
# ─────────────────────────────────────────────────────────────

def generate_sql(decomposition: dict, question: str = "") -> str:
    """
    Converts decomposition JSON into PostgreSQL SQL.
    """

    try:

        decomp_str = json.dumps(decomposition, indent=2)

        prompt = GENERATE_PROMPT.format(
            schema=SCHEMA,
            decomposition=decomp_str
        )

        raw_sql = _call_llm(prompt, max_tokens=512)

        return sanitise_sql(raw_sql)

    except Exception as e:

        tables = decomposition.get("tables", [])

        table = tables[0] if tables else "customers"

        return (
            f"SELECT * FROM {table} LIMIT 10; "
            f"-- fallback: generation error: {str(e)[:60]}"
        )


# ─────────────────────────────────────────────────────────────
# CALL 3: FIX SQL
# ─────────────────────────────────────────────────────────────

def fix_sql(sql: str, error: str, question: str) -> str:
    """
    Fixes broken SQL using database error messages.
    """

    try:

        prompt = FIX_PROMPT.format(
            schema=SCHEMA,
            question=question,
            sql=sql,
            error=error
        )

        fixed = _call_llm(prompt, max_tokens=512)

        return sanitise_sql(fixed)

    except Exception:

        # Return original SQL if fixing fails
        return sql