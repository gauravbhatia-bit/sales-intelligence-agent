# Sales Intelligence Agent

Ask business questions about sales data in plain English. A Gemini 2.0 Flash agent decides which analytics tool to call, runs it over a pandas data layer, and turns the result into a short business insight. A FastAPI backend serves it as a REST API; a Streamlit front end shows KPIs, answers and charts.

```
Streamlit UI  ──HTTP──▶  FastAPI backend  ──▶  Gemini 2.0 Flash (chooses a tool)
 (frontend/app.py)        (backend/main.py)          │
        ▲                        │                    ▼
        └──── answer + chart ────┘◀── pandas tools over data/sales_data.csv
```

## How the agent works

1. The question is sent to Gemini together with a system prompt that lists the available tools.
2. Gemini replies either with a direct answer or with a tool call as JSON: `{"tool": "get_top_products", "args": {"n": 5, "year": 2025}}`.
3. The backend parses the JSON, runs the matching pandas function and sends the result back to Gemini.
4. Gemini writes a 2–3 sentence business insight with specific numbers.
5. The API returns the answer, the tool used, the raw tool result and the latency in milliseconds.

The tool calls use a simple JSON protocol in the prompt (not Gemini's native function-calling API), so the routing logic stays visible in about 40 lines of Python.

### Tools (pandas)

| Tool | What it returns |
|---|---|
| `get_total_revenue(year=None)` | Total revenue, for one year or all data |
| `get_top_products(n=5, year=None)` | Top N products by revenue |
| `get_sales_by_region(year=None)` | Revenue per region, sorted |
| `get_monthly_trend(year=2025)` | Revenue by month for a year |
| `get_category_breakdown(year=None)` | Revenue per product category |

## REST API (FastAPI)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/status` | Number of rows, date range, model name |
| GET | `/summary` | Total revenue, total units, top product, top region |
| POST | `/ask` | Body `{"question": "..."}` → `answer`, `tool_used`, `tool_result`, `latency_ms` |

Interactive docs are at `/docs` once the server is running.

## Streamlit front end

- KPI row from `/summary` (revenue, units, top product, top region)
- Example question buttons and a free-text box that call `/ask`
- Shows the answer, the tool the agent used and the latency
- Plotly chart that matches the tool: bar (top products, categories), pie (regions), line (monthly trend), metric (total revenue)

## Data

`data/sales_data.csv` – 1,200 monthly rows from January 2024 to December 2025: 5 regions (North, South, East, West, Central), 10 products in 2 categories (Footwear, Apparel), with units sold, unit price and revenue.

## Run it locally

Requires Python 3.11.

```bash
git clone https://github.com/gauravbhatia-bit/sales-intelligence-agent.git
cd sales-intelligence-agent
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install streamlit plotly requests                  # front-end packages

echo "GEMINI_API_KEY=your_key_here" > .env

# Terminal 1 – backend (the front end expects port 8080)
uvicorn backend.main:app --port 8080 --reload

# Terminal 2 – front end
streamlit run frontend/app.py
```

Example request without the UI:

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Which region had the highest sales in 2025?"}'
```

## Tech stack

Python 3.11 · Gemini 2.0 Flash (`google-genai`) · FastAPI · Pydantic · pandas · Streamlit · Plotly · python-dotenv

## Author

Gaurav Bhatia – [Portfolio](https://gauravbhatia-bit.github.io) · [GitHub](https://github.com/gauravbhatia-bit)
