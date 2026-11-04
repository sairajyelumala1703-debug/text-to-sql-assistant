"""Core logic for the Text-to-SQL assistant.

No UI code lives here, so the Streamlit app and the verification script
share exactly the same logic. Works on the bundled sample table or on any CSV.
"""
import os
import re
import sqlite3
import time

import pandas as pd
from dotenv import load_dotenv
from google import genai

CSV_PATH = "fulfillment_clean.csv"
TABLE = "fulfillment"
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-flash-latest"]
MAX_ROWS = 200_000
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

PROMPT = """You are a SQL expert. Given this SQLite table schema:
{schema}

Table name: {table}
{hints}
Rules:
- Write ONLY one SQLite SELECT query. No explanation, no markdown.
- Always include the value you calculated (for example the total or count) in the output, not just the name.
- Give calculated columns clear names, such as total_cost or delayed_orders.
- Do not add filters (such as a status) unless the question asks for them.
- Dates are stored as text, so use SQLite date functions such as strftime.

Question: {question}
"""


class BlockedQueryError(Exception):
    """Raised when the model returns anything other than a single SELECT."""


def load_key(env_path="config.env"):
    load_dotenv(env_path)
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not found. Copy config.env.example to config.env and add your key.")
    return key.replace("GEMINI_API_KEY=", "").strip()


def clean_columns(df):
    """Make column names safe for SQL: letters, digits and underscores only."""
    seen, names = {}, []
    for c in df.columns:
        n = re.sub(r"\W+", "_", str(c).strip()).strip("_") or "col"
        if n[0].isdigit():
            n = "c_" + n
        k = n.lower()
        seen[k] = seen.get(k, 0) + 1
        names.append(n if seen[k] == 1 else f"{n}_{seen[k]}")
    out = df.copy()
    out.columns = names
    return out


def load_dataframe(df, table="data"):
    """In-memory SQLite copy of a DataFrame, opened read-only for queries."""
    if len(df) > MAX_ROWS:
        raise ValueError(f"File has {len(df):,} rows; the limit is {MAX_ROWS:,}.")
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    clean_columns(df).to_sql(table, conn, index=False)
    conn.execute("PRAGMA query_only = ON")
    return conn


def get_db(csv_path=CSV_PATH):
    return load_dataframe(pd.read_csv(csv_path), TABLE)


def get_schema_text(conn, table=TABLE):
    info = pd.read_sql(f'PRAGMA table_info("{table}")', conn)
    return info[["name", "type"]].to_string(index=False)


def column_hints(conn, table=TABLE, max_distinct=12):
    """Short notes for the prompt: allowed values of category columns and the date format.
    Only distinct category values and one date example are used, never whole rows."""
    info = pd.read_sql(f'PRAGMA table_info("{table}")', conn)
    hints = []
    for name, typ in zip(info["name"], info["type"]):
        if str(typ).upper() != "TEXT":
            continue
        vals = pd.read_sql(
            f'SELECT DISTINCT "{name}" AS v FROM "{table}" WHERE "{name}" IS NOT NULL LIMIT {max_distinct + 1}', conn
        )["v"].astype(str).tolist()
        if vals and DATE_RE.match(vals[0]) and len(vals) > 1:
            hints.append(f"- {name}: text dates like {vals[0]}")
        elif 0 < len(vals) <= max_distinct:
            hints.append(f"- {name}: one of {', '.join(vals)}")
    return ("Column notes:\n" + "\n".join(hints) + "\n") if hints else ""


def is_safe(sql):
    """Allow exactly one statement, and only SELECT / WITH."""
    s = sql.strip().rstrip(";").strip()
    return ";" not in s and s.lower().startswith(("select", "with"))


def clean_sql(text):
    return text.strip().replace("```sql", "").replace("```", "").strip()


def list_models(client):
    names = []
    try:
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            name = m.name.replace("models/", "")
            if "generateContent" in actions and "flash" in name:
                if not any(x in name for x in ("image", "tts", "live", "audio", "embed", "robotics")):
                    names.append(name)
    except Exception:
        pass
    names.sort(reverse=True)                 # newest names first
    names.sort(key=lambda n: "lite" in n)    # full models before lite ones
    return names + [m for m in FALLBACK_MODELS if m not in names]


class Assistant:
    def __init__(self, api_key, conn, client=None, table=TABLE):
        self.conn = conn
        self.table = table
        self.client = client or genai.Client(api_key=api_key)
        self.schema_text = get_schema_text(conn, table)
        self.hints = column_hints(conn, table)
        self.models = None
        self.working_model = None

    def generate(self, prompt, pause=2.0):
        """Try the models in turn; skip any that are busy or over quota."""
        if self.models is None:
            self.models = list_models(self.client)
        if self.working_model:
            order = [self.working_model] + [m for m in self.models if m != self.working_model]
        else:
            order = self.models
        last_error = None
        for m in order:
            try:
                resp = self.client.models.generate_content(model=m, contents=prompt)
                self.working_model = m
                return resp.text or ""
            except Exception as e:
                last_error = e
                time.sleep(pause)
        raise last_error

    def build_prompt(self, question):
        return PROMPT.format(schema=self.schema_text, table=self.table, hints=self.hints, question=question)

    def ask_database(self, question):
        return clean_sql(self.generate(self.build_prompt(question)))

    def run(self, question):
        sql = self.ask_database(question)
        if not is_safe(sql):
            raise BlockedQueryError(sql)
        return sql, pd.read_sql(sql, self.conn)
