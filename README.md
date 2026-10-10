# Sales Intelligence Agent

Ask business questions about sales data in plain English. By default, a local NLP pipeline uses TF-IDF bigram features and logistic regression to classify intent, then extracts entities and routes the question to a pandas analytics tool. Gemini 3.8 Flash can be enabled explicitly as a low-confidence fallback. A FastAPI backend serves the REST API; a Streamlit front end shows KPIs, NLP predictions, answers and charts.

## Live Demo

- [Open the Streamlit application](https://sales-intelligence-agent-5brv6ii7xelgzq7omewadn.streamlit.app/)
- [Explore the FastAPI documentation](https://sales-intelligence-api-22xn.onrender.com/docs)
- [Check the backend status](https://sales-intelligence-api-22xn.onrender.com/status)

```
Streamlit UI  ──HTTP──▶  FastAPI backend  ──▶  NLP intent + entity extraction
 (frontend/app.py)        (backend/main.py)          │
        ▲                        │                    ▼
        └──── answer + chart ────┘◀── pandas tools over data/sales_data.csv
```

## How the agent works

1. A TF-IDF vectorizer converts each question into unigram and bigram features.
2. Logistic regression predicts one of five intents and returns a probability-based confidence score.
3. Regex and dataset-derived vocabularies extract year, relative date ranges, top-N, region, category and product entities.
4. High-confidence predictions execute a deterministic pandas tool locally.
5. When Gemini is explicitly enabled, only predictions below `NLP_CONFIDENCE_THRESHOLD` fall back to the LLM.
6. The API returns the answer, tool result, NLP intent, entities, confidence, execution mode and latency.

The training and holdout utterances are versioned in `data/nlp_training_data.csv` and `data/nlp_evaluation_data.csv`, making the NLP behavior reproducible and measurable.

## NLP evaluation

Run the labelled holdout evaluation after installing dependencies:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_nlp.py
```

It prints accuracy, per-intent precision/recall/F1, and a confusion matrix. Add new utterances to the training CSV—not the evaluation CSV—when improving the classifier.

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
| POST | `/ask` | Body `{"question": "..."}` → answer, tool result, NLP prediction, mode and latency |
| POST | `/nlp/analyze` | Return only predicted intent, confidence and extracted entities |

Interactive docs are at `/docs` once the server is running.

## Streamlit front end

- KPI row from `/summary` (revenue, units, top product, top region)
- Example question buttons and a free-text box that call `/ask`
- Shows the answer, predicted intent, confidence, extracted entities, execution mode, tool and latency
- Plotly chart that matches the tool: bar (top products, categories), pie (regions), line (monthly trend), metric (total revenue)

## Data

`data/sales_data.csv` – 1,200 monthly rows from January 2024 to December 2025: 5 regions (North, South, East, West, Central), 10 products in 2 categories (Footwear, Apparel), with units sold, unit price and revenue.

## Run it locally

Requires Python 3.11.

On Windows, the quickest option is:

```powershell
.\start-local.ps1
```

This creates `.venv`, installs all dependencies, starts the backend and frontend, and checks the backend health endpoint. Stop both with `.\stop-local.ps1`.

## Deploy

The frontend reads `BACKEND_URL` from the environment and falls back to the local backend during development. See [DEPLOYMENT.md](DEPLOYMENT.md) for the Render + Streamlit Community Cloud deployment workflow.

```bash
git clone https://github.com/gauravbhatia-bit/sales-intelligence-agent.git
cd sales-intelligence-agent
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
# No API key is required for local mode.

# Terminal 1 – backend (the front end expects port 8080)
python -m uvicorn backend.main:app --port 8080 --reload

# Terminal 2 – front end
python -m streamlit run frontend/app.py
```

Example request without the UI:

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Which region had the highest sales in 2025?"}'
```

### Optional Gemini mode

Gemini is disabled by default so an old or exposed key cannot be used accidentally. To opt in for one PowerShell session, set `$env:ENABLE_GEMINI="true"` and `$env:GEMINI_API_KEY="your-new-key"` before starting Uvicorn. The app deliberately does not auto-load `.env`, so a previously stored key cannot be picked up accidentally. Never reuse an exposed key or commit credentials.

## Tech stack

Python 3.11 · scikit-learn · optional Gemini 3.8 Flash (`google-genai`) · FastAPI · Pydantic · pandas · Streamlit · Plotly

## Author

Gaurav Bhatia – [Portfolio](https://gauravbhatia-bit.github.io) · [GitHub](https://github.com/gauravbhatia-bit)
