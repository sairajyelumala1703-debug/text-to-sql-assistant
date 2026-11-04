# Text-to-SQL Assistant

Ask questions about a table in plain English. The Gemini API writes the SQL, the code checks that it is a single read-only `SELECT`, SQLite runs it, and the result appears as a table. It works on the bundled sample data or on **any CSV you upload**.

> **About the data:** `fulfillment_clean.csv` holds 500 *simulated* fulfillment records (warehouse, status, units, cost) that I generated and cleaned for this portfolio project. It is not company data.

## Who is it for?

- **People without SQL skills** (managers, sales or operations teams) who want quick answers from a spreadsheet or CSV export.
- **Analysts** who want a first-draft query to check and edit, instead of starting from a blank editor.
- **SQL learners** who can compare the model's query with their own and learn from the differences.

It is a prototype. It answers questions about one table at a time, and the generated SQL must always be read before the result is trusted.

## How to use it

1. **Open the app.** Run it locally (see Setup) or use a hosted link if one is available.
2. **Paste a free Gemini API key** in the sidebar. Get one from [Google AI Studio](https://aistudio.google.com). It is used only in your session.
3. **Pick data:** the sample warehouse data, or upload your own CSV (up to 10 MB and 200,000 rows).
4. **Ask a question** in plain English and read the generated SQL, the result table, and the chart if one fits.
5. **Download the result** as a CSV.

## How it works

1. You type a question, for example "How many orders were delayed in each warehouse?"
2. The table structure and a set of rules are sent to Gemini in a prompt. Gemini receives your question, the column names, the allowed values of category columns (for example the status values), and one date example. The other data rows are not sent.
3. Gemini returns one SQL query.
4. A safety check blocks anything that is not a single `SELECT` / `WITH` statement. The database connection is also opened read-only.
5. SQLite runs the query and the result is shown, with a chart when it fits.

If a model is busy or over its free quota, the code tries the next available model and retries.

## Setup

```bash
git clone https://github.com/sairajyelumala1703-debug/text-to-sql-assistant.git
cd text-to-sql-assistant
pip install -r requirements.txt
```

1. Get a free API key from [Google AI Studio](https://aistudio.google.com).
2. Copy `config.env.example` to `config.env` and put your key after the `=`, with no extra text:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   `config.env` is listed in `.gitignore`, so it is never committed.
3. Run the web app:
   ```bash
   streamlit run app.py
   ```
   It opens at `http://localhost:8501`. Click an example question or type your own.

Free-tier limits apply, so if you see a rate-limit message, wait a minute and retry.

## Hosting it online (optional)

To share a link, push this repo to GitHub and deploy it on [Streamlit Community Cloud](https://streamlit.io/cloud): choose the repo, set `app.py` as the main file, and deploy. Because the sidebar lets each visitor enter their own free Gemini key, you do not need to put your key in the app, and visitors do not use up your quota.

## Example questions, SQL and results

These were recorded from my own runs during development. The SQL is exactly what the model returned, and decimal values are rounded to 2 places here.

**How many orders were delayed in each warehouse?**
```sql
SELECT warehouse, COUNT(*) FROM fulfillment WHERE status = 'Delayed' GROUP BY warehouse
```
| warehouse | COUNT(*) |
|---|---|
| WH-EAST | 17 |
| WH-NORTH | 24 |
| WH-SOUTH | 35 |
| WH-WEST | 18 |

**What percentage of orders in each warehouse were delivered?**
```sql
SELECT warehouse, 100.0 * COUNT(CASE WHEN status = 'Delivered' THEN 1 END) / COUNT(*) AS delivered_percentage
FROM fulfillment GROUP BY warehouse
```
| warehouse | delivered_percentage |
|---|---|
| WH-EAST | 48.39 |
| WH-NORTH | 56.33 |
| WH-SOUTH | 51.16 |
| WH-WEST | 46.75 |

**What is the average fulfillment cost per warehouse?**
```sql
SELECT warehouse, AVG(fulfillment_cost) AS avg_fulfillment_cost FROM fulfillment GROUP BY warehouse
```
| warehouse | avg_fulfillment_cost |
|---|---|
| WH-EAST | 296.84 |
| WH-NORTH | 256.26 |
| WH-SOUTH | 274.48 |
| WH-WEST | 242.17 |

**How many orders were placed each month?**
```sql
SELECT strftime('%Y-%m', order_date) AS month, COUNT(order_id) AS order_count FROM fulfillment GROUP BY month;
```
| month | order_count |
|---|---|
| 2024-01 | 61 |
| 2024-02 | 53 |
| 2024-03 | 65 |
| 2024-04 | 58 |
| 2024-05 | 67 |
| 2024-06 | 67 |
| 2024-07 | 66 |
| 2024-08 | 63 |

**How many orders are there for each status?**
```sql
SELECT status, COUNT(*) AS order_count FROM fulfillment GROUP BY status;
```
| status | order_count |
|---|---|
| Cancelled | 69 |
| Delayed | 94 |
| Delivered | 258 |
| Unknown | 79 |

**What is the total number of units per warehouse across all orders?**
```sql
SELECT warehouse, SUM(units) AS total_units FROM fulfillment GROUP BY warehouse;
```
| warehouse | total_units |
|---|---|
| WH-EAST | 279 |
| WH-NORTH | 478 |
| WH-SOUTH | 501 |
| WH-WEST | 233 |

## A failure I found and fixed

I first asked for the total number of units *shipped* per warehouse. The model added `WHERE status = 'Delivered'` on its own, which I never asked for, so the totals were too low (WH-EAST 153 instead of 279, and so on). I found it by reading the generated SQL. The fix was a prompt rule: *"Do not add filters unless the question asks for them."* The same question, reworded, then returned the correct totals shown above.

## Verification

The prompt was refined after the recorded runs below, so re-run `verify.py` to see how the current version performs.

**Manual checks.** I checked 7 questions against answers I calculated separately with hand-written SQL. Six matched on the first run, and the units question above needed the prompt fix.

**Automated checks.** `verify.py` runs 25 test questions plus 3 safety tests:

- Each question's generated SQL is run, and its result is compared with a hand-written ground-truth query on the same data. Row order is ignored, numbers are compared with a small tolerance, and extra columns in the model's answer are accepted.
- The 25 questions cover counts, sums, averages, percentages, grouping by month, `HAVING`, top-N, and a window function (`ROW_NUMBER() OVER (PARTITION BY ...)`). Two of them test a common mix-up: "most delayed orders" (a count) versus "highest percentage of delayed orders" (a rate).
- The 3 safety tests ask the model to delete rows, drop the table, and update every row. They pass only if the request is blocked or the data is unchanged.
- API errors, such as free-tier rate limits, are reported separately and are not counted as failures.

```bash
python verify.py                 # fresh run of everything
python verify.py --resume        # continue after an interruption or API errors
python verify.py --pause 10      # wait longer between questions if you hit rate limits
python verify.py --ids 1,5,S2    # re-run only some tests (merged into earlier results)
```

Results are saved after every test to `verification_results.md` and `verification_results.csv`, with the generated SQL for every test.

## Limitations

- Uploaded files are loaded into memory for the session only, and the model sees the column names and category values described above. Do not upload confidential data without permission.

- Ambiguous wording changes the query, so always read the generated SQL before trusting a result.
- It works on one table at a time, with no joins across files. It is a learning project, not a production tool.
- Free-tier API limits can cause rate-limit errors.

## Project structure

```
app.py                    Streamlit web app (sample data or CSV upload)
text_to_sql.py            Core logic: prompt, model fallback, SELECT-only check
verify.py                 Automated verification (25 tests + 3 safety tests)
fulfillment_clean.csv     Simulated data (500 records)
config.env.example        Template for your API key
requirements.txt
```

**Tech:** Python, SQLite, Pandas, Streamlit, Google Gemini API (`google-genai`).
