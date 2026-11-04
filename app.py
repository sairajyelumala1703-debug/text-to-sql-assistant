import io
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from text_to_sql import TABLE, Assistant, get_db, is_safe, load_dataframe

st.set_page_config(page_title="Text-to-SQL Assistant", page_icon="🔎", layout="wide")
load_dotenv("config.env")

SAMPLE = "Sample data: warehouse fulfillment"
UPLOAD = "Upload my own CSV"
EXAMPLES = [
    "Which warehouse has the highest total fulfillment cost?",
    "How many orders were delayed in each warehouse?",
    "What percentage of orders in each warehouse were delivered?",
]
MAX_UPLOAD_MB = 10


def get_key(user_key):
    if user_key.strip():
        return user_key.strip()
    key = None
    try:
        if "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    key = key or os.getenv("GEMINI_API_KEY")
    return key.replace("GEMINI_API_KEY=", "").strip() if key else None


@st.cache_resource(show_spinner=False)
def build_assistant(key, data_bytes):
    if data_bytes is None:
        return Assistant(key, get_db(), table=TABLE)
    df = pd.read_csv(io.BytesIO(data_bytes))
    return Assistant(key, load_dataframe(df, "data"), table="data")


def set_question(q):
    st.session_state["question"] = q


st.title("🔎 Text-to-SQL Assistant")
st.caption("Ask questions about a table in plain English. Gemini writes the SQL, a read-only check validates it, and you see the result.")

# ---------------- sidebar: key and data ----------------
with st.sidebar:
    st.subheader("1. Gemini API key")
    user_key = st.text_input(
        "Your key (optional if the app already has one)", type="password",
        help="Get a free key at aistudio.google.com. It is used only in this session.",
    )
    st.subheader("2. Data")
    source = st.radio("Choose data", [SAMPLE, UPLOAD], label_visibility="collapsed")
    uploaded = st.file_uploader("CSV file (max 10 MB)", type="csv") if source == UPLOAD else None
    st.caption(
        "Sent to Gemini: your question, the column names, and the allowed values of category "
        "columns plus one date example. The other rows stay in your session."
    )

key = get_key(user_key)
if not key:
    st.info("Enter a Gemini API key in the sidebar to start. A free key is available from Google AI Studio.")
    st.stop()

data_bytes = None
if source == UPLOAD:
    if uploaded is None:
        st.info("Upload a CSV file in the sidebar to ask questions about your own data.")
        st.stop()
    if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"File is larger than {MAX_UPLOAD_MB} MB.")
        st.stop()
    data_bytes = uploaded.getvalue()

try:
    assistant = build_assistant(key, data_bytes)
except Exception as e:
    st.error(f"Could not load the data: {e}")
    st.stop()

with st.expander("Table preview and columns", expanded=False):
    st.dataframe(pd.read_sql(f'SELECT * FROM "{assistant.table}" LIMIT 5', assistant.conn), width="stretch")
    st.code(assistant.schema_text)

# ---------------- question ----------------
if source == SAMPLE:
    st.write("Try an example:")
    cols = st.columns(len(EXAMPLES))
    for c, q in zip(cols, EXAMPLES):
        c.button(q, on_click=set_question, args=(q,), width="stretch")

question = st.text_input("Your question", key="question")

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Writing the SQL..."):
        try:
            sql = assistant.ask_database(question)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                st.warning("The free API limit was reached. Wait a minute and try again.")
            elif "API_KEY_INVALID" in msg or "API key not valid" in msg:
                st.error("That API key was not accepted. Check it and try again.")
            else:
                st.error(f"Could not reach the model: {msg[:200]}")
            st.stop()

    st.subheader("Generated SQL")
    st.code(sql, language="sql")
    st.caption("Always read the SQL before trusting a result.")

    if not is_safe(sql):
        st.error("Blocked: only a single SELECT query is allowed.")
        st.stop()

    try:
        result = pd.read_sql(sql, assistant.conn)
    except Exception as e:
        st.error(f"The query failed to run: {e}")
        st.stop()

    st.subheader("Result")
    st.dataframe(result, width="stretch")
    st.download_button("Download result as CSV", result.to_csv(index=False), "result.csv", "text/csv")

    if result.shape[1] == 2 and pd.api.types.is_numeric_dtype(result.iloc[:, 1]) and 2 <= len(result) <= 30:
        st.bar_chart(result.set_index(result.columns[0]))

    st.caption(f"Model used: {assistant.working_model or 'n/a'}")
