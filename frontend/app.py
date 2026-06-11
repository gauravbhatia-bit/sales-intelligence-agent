import streamlit as st
import requests
import plotly.express as px
API = "http://localhost:8080"

API = "http://localhost:8080"

st.set_page_config(page_title="Sales Intelligence Agent", page_icon="??", layout="wide")

st.markdown('''
<style>
.main-header {font-size: 2rem; font-weight: 700; color: #01696f;}
.sub-header {font-size: 1rem; color: #7a7974; margin-bottom: 2rem;}
.tool-badge {background: #cedcd8; color: #01696f; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;}
.answer-box {background: #f9f8f5; border-left: 3px solid #01696f; padding: 1rem; border-radius: 4px; margin: 1rem 0;}
</style>
''', unsafe_allow_html=True)

st.markdown('<div class="main-header">?? Sales Intelligence Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Powered by Gemini 1.5 Flash � Tool Calling � Pandas Analytics</div>', unsafe_allow_html=True)

try:
    summary = requests.get(f"{API}/summary", timeout=5).json()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"EUR {summary['total_revenue']:,.0f}")
    col2.metric("Total Units Sold", f"{summary['total_units']:,}")
    col3.metric("Top Product", summary['top_product'])
    col4.metric("Top Region", summary['top_region'])
except:
    st.warning("Backend not running. Start with: uvicorn backend.main:app --reload")

st.divider()
st.subheader("Ask the Agent")

EXAMPLES = [
    "What was the total revenue in 2025?",
    "Which are the top 5 products by revenue?",
    "Which region had the highest sales?",
    "Show me the monthly revenue trend for 2025",
    "What is the revenue breakdown by category?",
    "What was total revenue in 2024?",
]

st.write("Try these questions:")
cols = st.columns(3)
for i, q in enumerate(EXAMPLES):
    if cols[i % 3].button(q, key=f"btn_{i}"):
        st.session_state["question"] = q

question = st.text_input("Or type your own question:", value=st.session_state.get("question", ""), placeholder="e.g. Which product sold the most in 2025?")

if st.button("Ask Agent", type="primary") and question:
    with st.spinner("Agent is thinking..."):
        try:
            res = requests.post(f"{API}/ask", json={"question": question}, timeout=30).json()
            st.markdown(f'<div class="answer-box"><b>Answer:</b><br>{res["answer"]}</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if res.get("tool_used"):
                    st.markdown(f'Tool used: <span class="tool-badge">{res["tool_used"]}</span>', unsafe_allow_html=True)
                else:
                    st.info("No tool needed - answered directly")
            with col2:
                st.caption(f"Latency: {res['latency_ms']}ms")

            if res.get("tool_result"):
                result = res["tool_result"]
                st.subheader("Data Visualisation")
                if "top_products" in result:
                    df_plot = pd.DataFrame(result["top_products"])
                    fig = px.bar(df_plot, x="product", y="revenue", title="Top Products by Revenue", color="revenue", color_continuous_scale="teal")
                    st.plotly_chart(fig, use_container_width=True)
                elif "sales_by_region" in result:
                    df_plot = pd.DataFrame(result["sales_by_region"])
                    fig = px.pie(df_plot, names="region", values="revenue", title="Revenue by Region")
                    st.plotly_chart(fig, use_container_width=True)
                elif "monthly_trend" in result:
                    df_plot = pd.DataFrame(result["monthly_trend"])
                    fig = px.line(df_plot, x="month", y="revenue", title=f"Monthly Revenue Trend {result.get('year','')}", markers=True, color_discrete_sequence=["#01696f"])
                    st.plotly_chart(fig, use_container_width=True)
                elif "category_breakdown" in result:
                    df_plot = pd.DataFrame(result["category_breakdown"])
                    fig = px.bar(df_plot, x="category", y="revenue", title="Revenue by Category", color="category")
                    st.plotly_chart(fig, use_container_width=True)
                elif "total_revenue" in result:
                    st.metric("Total Revenue", f"EUR {result['total_revenue']:,.2f}")
        except Exception as e:
            st.error(f"Error: {e}")
