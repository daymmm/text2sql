"""
database.py
-----------
All PostgreSQL connection and query execution lives here.

WHAT THIS FILE DOES:
  - Connects to PostgreSQL using .env credentials
  - Executes any SQL string safely
  - NEVER raises exceptions — always returns structured result dict
  - Provides a test_connection() health check for startup

WHY A SEPARATE FILE?
  Every other file imports from here. If you change DB settings,
  you change it in ONE place only.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """
    Creates and returns a live PostgreSQL connection.
    Uses environment variables so credentials never appear in code.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "classicmodels"),
        user=os.getenv("DB_USER", "subhampoudel"),
        password=os.getenv("DB_PASSWORD", "12345"),
        connect_timeout=10
    )


def execute_query(sql: str) -> dict:
    """
    Runs a SQL string against PostgreSQL.

    Returns a dict — NEVER raises:
    {
        "columns":  ["col1", "col2"],   # column names from cursor
        "rows":     [(val, val), ...],   # raw tuples
        "rowcount": 5,                   # how many rows returned
        "error":    None | "error msg"  # None = success
    }

    The pipeline checks result["error"] to decide whether to retry.
    """
    result = {"columns": [], "rows": [], "rowcount": 0, "error": None}
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.description:
            result["columns"] = [desc[0] for desc in cursor.description]
            result["rows"]    = cursor.fetchall()
            result["rowcount"] = len(result["rows"])
            
        conn.commit()

    except psycopg2.OperationalError as e:
        result["error"] = f"Connection error: {str(e)}"
    except psycopg2.ProgrammingError as e:
        result["error"] = f"SQL error: {str(e)}"
    except psycopg2.DataError as e:
        result["error"] = f"Data error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return result


def init_seed():
    """Loads seed.sql into the PostgreSQL database if the tables are empty."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'customers';")
        if cursor.fetchone()[0] == 0:
            print("Loading seed.sql into database...")
            with open("seed.sql", "r") as f:
                sql_script = f.read()
            cursor.execute(sql_script)
            conn.commit()
            print("Seed data loaded successfully.")
        conn.close()
    except Exception as e:
        print(f"Failed to load seed data: {e}")

# Run seed initialization when the file is loaded
init_seed()

def test_connection() -> bool:
    """Returns True if DB is reachable, False otherwise."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False

print("DATABASE FILE LOADED")