import json
import os
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from backend.nlp_router import NlpRouter

app = FastAPI(title="Sales Intelligence Agent", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8501,http://127.0.0.1:8501",
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "sales_data.csv"
df = pd.read_csv(DATA_PATH, parse_dates=["date"])
print(f"[DATA] Loaded {len(df)} rows")


def filter_data(
    year: int | None = None,
    region: str | None = None,
    category: str | None = None,
    product: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    d = df
    if year:
        d = d[d["date"].dt.year == year]
    if region:
        d = d[d["region"].str.casefold() == region.casefold()]
    if category:
        d = d[d["category"].str.casefold() == category.casefold()]
    if product:
        d = d[d["product"].str.casefold() == product.casefold()]
    if start_date:
        d = d[d["date"] >= pd.Timestamp(start_date)]
    if end_date:
        d = d[d["date"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)]
    return d


def get_total_revenue(
    year: int | None = None,
    region: str | None = None,
    category: str | None = None,
    product: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    d = filter_data(year, region, category, product, start_date, end_date)
    return {
        "total_revenue": round(d["revenue"].sum(), 2),
        "year": year or "all",
        "matched_rows": len(d),
        "start_date": start_date,
        "end_date": end_date,
    }


def get_top_products(
    n: int = 5,
    year: int | None = None,
    region: str | None = None,
    category: str | None = None,
) -> dict:
    d = filter_data(year, region, category)
    top = d.groupby("product")["revenue"].sum().nlargest(n).reset_index()
    return {"top_products": top.to_dict(orient="records")}


def get_sales_by_region(
    year: int | None = None,
    category: str | None = None,
    product: str | None = None,
) -> dict:
    d = filter_data(year, category=category, product=product)
    reg = d.groupby("region")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
    return {"sales_by_region": reg.to_dict(orient="records")}


def get_monthly_trend(
    year: int = 2025,
    region: str | None = None,
    category: str | None = None,
    product: str | None = None,
) -> dict:
    d = filter_data(year, region, category, product)
    trend = d.groupby(d["date"].dt.month)["revenue"].sum().reset_index()
    trend.columns = ["month", "revenue"]
    trend["revenue"] = trend["revenue"].round(2)
    return {"monthly_trend": trend.to_dict(orient="records"), "year": year}


def get_category_breakdown(
    year: int | None = None,
    region: str | None = None,
    product: str | None = None,
) -> dict:
    d = filter_data(year, region, product=product)
    cat = d.groupby("category")["revenue"].sum().reset_index()
    return {"category_breakdown": cat.to_dict(orient="records")}

TOOLS = {
    "get_total_revenue": get_total_revenue,
    "get_top_products": get_top_products,
    "get_sales_by_region": get_sales_by_region,
    "get_monthly_trend": get_monthly_trend,
    "get_category_breakdown": get_category_breakdown,
}

nlp_router = NlpRouter(
    BASE_DIR / "data" / "nlp_training_data.csv",
    products=df["product"].dropna().unique(),
    regions=df["region"].dropna().unique(),
    categories=df["category"].dropna().unique(),
)
NLP_CONFIDENCE_THRESHOLD = float(os.getenv("NLP_CONFIDENCE_THRESHOLD", "0.45"))

TOOL_DESCRIPTIONS = '''
You are a Sales Intelligence Agent. You have access to these tools:
1. get_total_revenue(year: int = None) - Get total revenue. Optionally filter by year (2024 or 2025).
2. get_top_products(n: int = 5, year: int = None) - Get top N products by revenue.
3. get_sales_by_region(year: int = None) - Get revenue breakdown by region.
4. get_monthly_trend(year: int = 2025) - Get month-by-month revenue trend.
5. get_category_breakdown(year: int = None) - Get revenue by product category.

To use a tool respond with ONLY this JSON format:
{"tool": "tool_name", "args": {"param": value}}

If you can answer directly without a tool, respond normally.
After getting tool results, provide a clear business insight answer.
'''

from google import genai

GEMINI_ENABLED = os.getenv("ENABLE_GEMINI", "false").lower() == "true"
GEMINI_KEY = os.getenv("GEMINI_API_KEY") if GEMINI_ENABLED else None
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)
    print(f"[LLM] {MODEL_NAME} ready")
else:
    client = None
    print("[LLM] Gemini disabled; using local pandas routing")


def run_local_agent(question: str, prediction: dict[str, object] | None = None) -> dict:
    """Route a question with the trained NLP model and execute a pandas tool."""
    start = time.time()
    prediction = prediction or nlp_router.predict(question)
    intent = str(prediction["intent"])
    entities = dict(prediction["entities"])
    year = entities.get("year")
    common_filters = {
        key: entities[key]
        for key in (
            "year",
            "region",
            "category",
            "product",
            "start_date",
            "end_date",
        )
        if key in entities
    }

    if intent == "monthly_trend":
        tool_used = "get_monthly_trend"
        tool_result = get_monthly_trend(
            year=int(year) if year else 2025,
            region=entities.get("region"),
            category=entities.get("category"),
            product=entities.get("product"),
        )
        rows = tool_result["monthly_trend"]
        if rows:
            peak = max(rows, key=lambda row: row["revenue"])
            answer = (
                f"Revenue peaked in month {peak['month']} of {tool_result['year']} "
                f"at EUR {peak['revenue']:,.2f}."
            )
        else:
            answer = f"No matching monthly sales records were found for {tool_result['year']}."
    elif intent == "sales_by_region":
        if entities.get("region"):
            tool_used = "get_total_revenue"
            tool_result = get_total_revenue(**common_filters)
            answer = (
                f"{entities['region']} revenue was "
                f"EUR {tool_result['total_revenue']:,.2f}."
            )
        else:
            tool_used = "get_sales_by_region"
            tool_result = get_sales_by_region(
                year=int(year) if year else None,
                category=entities.get("category"),
                product=entities.get("product"),
            )
            rows = tool_result["sales_by_region"]
            answer = (
                f"{rows[0]['region']} had the highest revenue at EUR {rows[0]['revenue']:,.2f}."
                if rows
                else "No matching regional sales records were found."
            )
    elif intent == "category_breakdown":
        if entities.get("category"):
            tool_used = "get_total_revenue"
            tool_result = get_total_revenue(**common_filters)
            answer = (
                f"{entities['category']} revenue was "
                f"EUR {tool_result['total_revenue']:,.2f}."
            )
        else:
            tool_used = "get_category_breakdown"
            tool_result = get_category_breakdown(
                year=int(year) if year else None,
                region=entities.get("region"),
                product=entities.get("product"),
            )
            rows = sorted(
                tool_result["category_breakdown"],
                key=lambda row: row["revenue"],
                reverse=True,
            )
            answer = (
                f"{rows[0]['category']} was the leading category at EUR {rows[0]['revenue']:,.2f}."
                if rows
                else "No matching category sales records were found."
            )
    elif intent == "top_products":
        if entities.get("product"):
            tool_used = "get_total_revenue"
            tool_result = get_total_revenue(**common_filters)
            answer = (
                f"{entities['product']} revenue was "
                f"EUR {tool_result['total_revenue']:,.2f}."
            )
        else:
            tool_used = "get_top_products"
            tool_result = get_top_products(
                n=int(entities.get("top_n", 5)),
                year=int(year) if year else None,
                region=entities.get("region"),
                category=entities.get("category"),
            )
            rows = tool_result["top_products"]
            answer = (
                f"{rows[0]['product']} was the top product at EUR {rows[0]['revenue']:,.2f}."
                if rows
                else "No matching product sales records were found."
            )
    else:
        tool_used = "get_total_revenue"
        tool_result = get_total_revenue(**common_filters)
        if tool_result["matched_rows"] == 0 and entities.get("start_date"):
            start_date = entities["start_date"]
            end_date = entities.get("end_date", start_date)
            date_label = start_date if start_date == end_date else f"{start_date} to {end_date}"
            answer = f"No sales records were found for {date_label}."
        else:
            period = year if year else "all available years"
            if entities.get("start_date"):
                period = entities["start_date"]
                if entities.get("end_date") != entities["start_date"]:
                    period = f"{period} to {entities['end_date']}"
            answer = f"Total revenue for {period} was EUR {tool_result['total_revenue']:,.2f}."

    latency = round((time.time() - start) * 1000, 1)
    return {
        "answer": answer,
        "tool_used": tool_used,
        "tool_result": tool_result,
        "latency_ms": latency,
        "mode": "local_nlp",
        "nlp": prediction,
    }

def run_agent(question: str) -> dict:
    prediction = nlp_router.predict(question)
    if not client or float(prediction["confidence"]) >= NLP_CONFIDENCE_THRESHOLD:
        return run_local_agent(question, prediction)
    start = time.time()
    prompt = f"{TOOL_DESCRIPTIONS}\n\nUser question: {question}\n\nRespond with tool JSON or direct answer:"
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    raw = response.text.strip()
    answer = raw
    tool_used = None
    tool_result = None
    try:
        clean = raw.replace("`json", "").replace("`", "").strip()
        tool_call = json.loads(clean)
        if "tool" in tool_call:
            tool_name = tool_call["tool"]
            tool_args = tool_call.get("args", {})
            if tool_name in TOOLS:
                tool_result = TOOLS[tool_name](**tool_args)
                tool_used = tool_name
                followup = f"The user asked: {question}\nYou called tool {tool_name} and got: {json.dumps(tool_result)}\nProvide a clear business insight in 2-3 sentences with specific numbers."
                final = client.models.generate_content(model=MODEL_NAME, contents=followup)
                answer = final.text.strip()
            else:
                answer = raw
    except (json.JSONDecodeError, KeyError):
        answer = raw
    latency = round((time.time() - start) * 1000, 1)
    return {
        "answer": answer,
        "tool_used": tool_used,
        "tool_result": tool_result,
        "latency_ms": latency,
        "mode": "gemini",
        "nlp": prediction,
    }

class QuestionRequest(BaseModel):
    question: str

@app.get("/")
def root():
    return {"status": "ok", "service": "Sales Intelligence Agent v2"}

@app.get("/status")
def status():
    return {
        "rows": len(df),
        "date_range": f"{df['date'].min().date()} to {df['date'].max().date()}",
        "llm": MODEL_NAME,
        "llm_enabled": GEMINI_ENABLED,
        "llm_configured": client is not None,
        "nlp_model": "TF-IDF bigrams + logistic regression",
        "nlp_confidence_threshold": NLP_CONFIDENCE_THRESHOLD,
    }

@app.post("/ask")
def ask(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return run_agent(req.question)


@app.post("/nlp/analyze")
def analyze_nlp(req: QuestionRequest):
    """Expose intent, confidence and entities without running an analytics tool."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return nlp_router.predict(req.question)

@app.get("/summary")
def summary():
    return {
        "total_revenue": round(df["revenue"].sum(), 2),
        "total_units": int(df["units_sold"].sum()),
        "top_product": df.groupby("product")["revenue"].sum().idxmax(),
        "top_region": df.groupby("region")["revenue"].sum().idxmax()
    }
