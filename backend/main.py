import os, time, json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

app = FastAPI(title="Sales Intelligence Agent", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sales_data.csv")
df = pd.read_csv(DATA_PATH, parse_dates=["date"])
print(f"[DATA] Loaded {len(df)} rows")

def get_total_revenue(year: int = None) -> dict:
    d = df[df["date"].dt.year == year] if year else df
    return {"total_revenue": round(d["revenue"].sum(), 2), "year": year or "all"}

def get_top_products(n: int = 5, year: int = None) -> dict:
    d = df[df["date"].dt.year == year] if year else df
    top = d.groupby("product")["revenue"].sum().nlargest(n).reset_index()
    return {"top_products": top.to_dict(orient="records")}

def get_sales_by_region(year: int = None) -> dict:
    d = df[df["date"].dt.year == year] if year else df
    reg = d.groupby("region")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
    return {"sales_by_region": reg.to_dict(orient="records")}

def get_monthly_trend(year: int = 2025) -> dict:
    d = df[df["date"].dt.year == year]
    trend = d.groupby(d["date"].dt.month)["revenue"].sum().reset_index()
    trend.columns = ["month", "revenue"]
    trend["revenue"] = trend["revenue"].round(2)
    return {"monthly_trend": trend.to_dict(orient="records"), "year": year}

def get_category_breakdown(year: int = None) -> dict:
    d = df[df["date"].dt.year == year] if year else df
    cat = d.groupby("category")["revenue"].sum().reset_index()
    return {"category_breakdown": cat.to_dict(orient="records")}

TOOLS = {
    "get_total_revenue": get_total_revenue,
    "get_top_products": get_top_products,
    "get_sales_by_region": get_sales_by_region,
    "get_monthly_trend": get_monthly_trend,
    "get_category_breakdown": get_category_breakdown,
}

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
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)
    print("[LLM] Gemini 2.0 Flash ready")
else:
    client = None
    print("[LLM] WARNING: No GEMINI_API_KEY found")

def run_agent(question: str) -> dict:
    if not client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    start = time.time()
    prompt = f"{TOOL_DESCRIPTIONS}\n\nUser question: {question}\n\nRespond with tool JSON or direct answer:"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    raw = response.text.strip()
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
                final = model.generate_content(followup)
                answer = final.text.strip()
            else:
                answer = raw
    except (json.JSONDecodeError, KeyError):
        answer = raw
    latency = round((time.time() - start) * 1000, 1)
    return {"answer": answer, "tool_used": tool_used, "tool_result": tool_result, "latency_ms": latency}

class QuestionRequest(BaseModel):
    question: str

@app.get("/")
def root():
    return {"status": "ok", "service": "Sales Intelligence Agent v2"}

@app.get("/status")
def status():
    return {"rows": len(df), "date_range": f"{df['date'].min().date()} to {df['date'].max().date()}", "llm": "gemini-1.5-flash"}

@app.post("/ask")
def ask(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return run_agent(req.question)

@app.get("/summary")
def summary():
    return {
        "total_revenue": round(df["revenue"].sum(), 2),
        "total_units": int(df["units_sold"].sum()),
        "top_product": df.groupby("product")["revenue"].sum().idxmax(),
        "top_region": df.groupby("region")["revenue"].sum().idxmax()
    }
