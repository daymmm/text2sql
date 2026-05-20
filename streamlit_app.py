"""
streamlit_app.py
----------------
The main UI. Run with: streamlit run streamlit_app.py

LAYOUT:
  Left sidebar  → DB status, category browser from your CSV
  Main area     → Chat interface + pipeline output

WHAT IT SHOWS PER QUERY:
  1. Decomposition (intent, tables, columns, filters, joins)
  2. Generated SQL with syntax highlighting
  3. Results table (scrollable dataframe)
  4. Execution metadata (latency, retry, status)
"""

try:
    import streamlit as st
except ImportError as exc:
    raise ImportError(
        "Missing dependency: streamlit. Install it with 'pip install streamlit' "
        "and rerun the app."
    ) from exc

import pandas as pd
import json
from pathlib import Path

from executor import run_pipeline
from database import test_connection
from csv_loader import load_benchmark, get_categories, get_by_category

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Text-to-SQL Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #666;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        border-left: 3px solid #4CAF50;
        margin: 0.3rem 0;
    }
    .decomp-card {
        background: #f0f4ff;
        border-radius: 8px;
        padding: 1rem;
        border-left: 3px solid #4361ee;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .status-success { color: #2e7d32; font-weight: 600; }
    .status-failed  { color: #c62828; font-weight: 600; }
    .status-retry   { color: #e65100; font-weight: 600; }
    .category-tag {
        display: inline-block;
        background: #e8eaf6;
        color: #3949ab;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗄️ Text-to-SQL Assistant")
    st.markdown("---")

    # DB connection status
    db_ok = test_connection()
    if db_ok:
        st.success("✅ Database connected")
    else:
        st.error("❌ Database offline")
        st.caption("Check your .env DB settings")

    st.markdown("---")

    # Benchmark CSV browser
    st.markdown("### 📋 Benchmark Questions")
    st.caption("Click any question to run it")

    try:
        categories = get_categories()
        selected_cat = st.selectbox("Filter by category", ["All"] + categories)

        if selected_cat == "All":
            all_qs = load_benchmark()
        else:
            all_qs = get_by_category(selected_cat)

        for q in all_qs:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    f"{q['number']}. {q['question']}",
                    key=f"q_{q['number']}",
                    use_container_width=True
                ):
                    st.session_state.prefill_question = q["question"]
            with col2:
                st.markdown(
                    f"<span class='category-tag'>{q['category'].split()[0]}</span>",
                    unsafe_allow_html=True
                )
    except Exception as e:
        st.warning(f"Could not load benchmark: {e}")

    st.markdown("---")

    # Query log viewer
    st.markdown("### 📝 Recent Logs")
    log_file = Path("logs/query_logs.json")
    if log_file.exists():
        try:
            with open(log_file) as f:
                logs = json.load(f)
            if logs:
                recent = logs[-5:][::-1]
                for log in recent:
                    icon = "✅" if log.get("status") == "success" else "❌"
                    st.caption(f"{icon} {log.get('question','')[:35]}...")
            else:
                st.caption("No queries yet")
        except Exception:
            st.caption("Log file empty")


# ── MAIN AREA ─────────────────────────────────────────────────
st.markdown('<div class="main-header">🗄️ Text-to-SQL Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Ask questions about the ClassicModels database in plain English</div>', unsafe_allow_html=True)

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prefill_question" not in st.session_state:
    st.session_state.prefill_question = ""

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.write(msg["content"])
        else:
            # Show decomposition
            if msg.get("decomposition"):
                d = msg["decomposition"]
                decomp_html = f"""
                <div class="decomp-card">
                <b>🧠 Query Understanding</b><br>
                <b>Intent:</b> {d.get('intent','—')}<br>
                <b>Tables:</b> {', '.join(d.get('tables', [])) or '—'}<br>
                <b>Columns:</b> {', '.join(d.get('columns', [])) or '—'}<br>
                <b>Filters:</b> {', '.join(d.get('filters', [])) or 'None'}<br>
                <b>Joins:</b>   {', '.join(d.get('joins',   [])) or 'None'}<br>
                <b>Group By:</b>{', '.join(d.get('group_by',[])) or 'None'}
                </div>
                """
                st.markdown(decomp_html, unsafe_allow_html=True)

            # Show SQL
            if msg.get("sql"):
                st.code(msg["sql"], language="sql")

            # Show result table
            if msg.get("result") and len(msg["result"]) > 0:
                df = pd.DataFrame(msg["result"])
                st.dataframe(df, use_container_width=True)
                st.caption(f"↳ {len(msg['result'])} rows returned")
            elif msg.get("status") == "success":
                st.info("Query ran successfully — no rows returned")

            # Status line
            status  = msg.get("status", "")
            latency = msg.get("latency_ms", 0)
            retry   = msg.get("retry", False)
            error   = msg.get("error", "")

            if status == "success":
                status_line = f'<span class="status-success">✅ Success</span>'
            elif status == "failed":
                status_line = f'<span class="status-failed">❌ Failed: {error}</span>'
            elif status == "blocked":
                status_line = f'<span class="status-failed">🚫 Blocked: {error}</span>'
            else:
                status_line = f'<span class="status-failed">❌ Error: {error}</span>'

            retry_badge = ' <span class="category-tag">🔄 Retried</span>' if retry else ""
            st.markdown(
                f"{status_line}{retry_badge} &nbsp;·&nbsp; {latency}ms",
                unsafe_allow_html=True
            )

# ── CHAT INPUT ────────────────────────────────────────────────
prefill = st.session_state.prefill_question
question = st.chat_input("Ask a question about your data...")

# Use prefilled question from sidebar click
if prefill and not question:
    question = prefill
    st.session_state.prefill_question = ""

if question:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    # Run pipeline
    with st.chat_message("assistant"):
        with st.spinner("🧠 Decomposing → Generating SQL → Executing..."):
            output = run_pipeline(question)

        decomp  = output.get("decomposition", {})
        sql     = output.get("sql", "")
        result  = output.get("result", [])
        status  = output.get("status", "failed")
        retry   = output.get("retry", False)
        error   = output.get("error", "")
        latency = output.get("latency_ms", 0)

        # Render decomposition
        if decomp:
            decomp_html = f"""
            <div class="decomp-card">
            <b>🧠 Query Understanding</b><br>
            <b>Intent:</b> {decomp.get('intent','—')}<br>
            <b>Tables:</b> {', '.join(decomp.get('tables', [])) or '—'}<br>
            <b>Columns:</b> {', '.join(decomp.get('columns', [])) or '—'}<br>
            <b>Filters:</b> {', '.join(decomp.get('filters', [])) or 'None'}<br>
            <b>Joins:</b>   {', '.join(decomp.get('joins',   [])) or 'None'}<br>
            <b>Group By:</b>{', '.join(decomp.get('group_by',[])) or 'None'}
            </div>
            """
            st.markdown(decomp_html, unsafe_allow_html=True)

        # Render SQL
        if sql:
            st.code(sql, language="sql")

        # Render results
        if status == "success":
            if result:
                df = pd.DataFrame(result)
                st.dataframe(df, use_container_width=True)
                st.caption(f"↳ {len(result)} rows returned")
            else:
                st.info("Query ran successfully — no rows returned")

        # Status line
        if status == "success":
            status_line = '<span class="status-success">✅ Success</span>'
        elif status == "failed":
            status_line = f'<span class="status-failed">❌ Failed: {error}</span>'
        elif status == "blocked":
            status_line = f'<span class="status-failed">🚫 Blocked: {error}</span>'
        else:
            status_line = f'<span class="status-failed">❌ Error: {error}</span>'

        retry_badge = ' <span class="category-tag">🔄 Retried</span>' if retry else ""
        st.markdown(
            f"{status_line}{retry_badge} &nbsp;·&nbsp; {latency}ms",
            unsafe_allow_html=True
        )

        # Save to session
        st.session_state.messages.append({
            "role":          "assistant",
            "decomposition": decomp,
            "sql":           sql,
            "result":        result,
            "status":        status,
            "retry":         retry,
            "error":         error,
            "latency_ms":    latency
        })

    st.rerun()