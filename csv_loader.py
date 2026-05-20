"""
csv_loader.py
-------------
Loads YOUR benchmark CSV (data/benchmark.csv) — the Task 2 dataset.

YOUR CSV COLUMNS:
  Question_Number, Question, Query_Category, Intent,
  Tables, Columns, Filters, Joins, Group_By, SQL_Query

WHAT THIS FILE DOES:
  - load_benchmark()         → returns list of all 50 question dicts
  - get_question_by_number() → get one question by its number
  - get_by_category()        → filter to Simple SELECT / JOIN / etc.
  - get_ground_truth_sql()   → returns the SQL_Query (ground truth)
    for a given question — used by evaluate.py to compare outputs

WHY USE THIS CSV?
  The SQL_Query column is your "ground truth". The evaluator
  runs your pipeline on each Question, gets the generated SQL,
  executes it, and compares results against running the ground truth.
"""

import csv
from pathlib import Path

CSV_PATH = Path("data/benchmark.csv")


def load_benchmark() -> list[dict]:
    """
    Loads all rows from the benchmark CSV.

    Returns a list of dicts, one per question:
    {
      "number":    1,
      "question":  "List all products",
      "category":  "Simple SELECT",
      "intent":    "Retrieve all product records",
      "tables":    "products",
      "columns":   "*",
      "filters":   "None",
      "joins":     "None",
      "group_by":  "None",
      "ground_truth_sql": "SELECT * FROM products;"
    }
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Benchmark CSV not found at {CSV_PATH}")

    questions = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append({
                "number":           int(row["Question_Number"]),
                "question":         row["Question"].strip(),
                "category":         row["Query_Category"].strip(),
                "intent":           row["Intent"].strip(),
                "tables":           row["Tables"].strip(),
                "columns":          row["Columns"].strip(),
                "filters":          row["Filters"].strip(),
                "joins":            row["Joins"].strip(),
                "group_by":         row["Group_By"].strip(),
                "ground_truth_sql": row["SQL_Query"].strip(),
            })
    return questions


def get_categories() -> list[str]:
    """Returns sorted list of unique Query_Category values."""
    data = load_benchmark()
    return sorted(set(q["category"] for q in data))


def get_by_category(category: str) -> list[dict]:
    """Returns only questions matching the given category."""
    return [q for q in load_benchmark() if q["category"] == category]


def get_question_by_number(number: int) -> dict | None:
    """Returns a single question dict by its number, or None."""
    for q in load_benchmark():
        if q["number"] == number:
            return q
    return None


def get_ground_truth_sql(question_text: str) -> str | None:
    """
    Looks up the ground truth SQL for a given question string.
    Used by the evaluator to compare results.
    Returns None if question not found.
    """
    for q in load_benchmark():
        if q["question"].lower().strip() == question_text.lower().strip():
            return q["ground_truth_sql"]
    return None