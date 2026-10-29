"""Monday Coffee Expansion Dashboard.  Run:  streamlit run app.py"""
from pathlib import Path
import altair as alt
import streamlit as st
from logic import (PICKS, load_data, city_metrics, expansion_scores,
                   monthly_revenue, top_products)

st.set_page_config(page_title="Monday Coffee Expansion Dashboard", page_icon="☕", layout="wide")
ACCENT, MUTED = "#b4571e", "#9aa7b4"


@st.cache_data
def get_data():
    return load_data(Path(__file__).parent / "data")


city, df = get_data()
metrics = city_metrics(city, df)

# ---------------- Sidebar ----------------
st.sidebar.header("Filters")
choice = st.sidebar.selectbox("City", ["All"] + sorted(metrics["city_name"]))
exclude_partial = st.sidebar.checkbox("Exclude partial month (Oct 2024)", value=True)

st.sidebar.header("Expansion score weights")
st.sidebar.caption("0 ignores a metric; higher means more important.")
w_rev = st.sidebar.slider("Revenue", 0, 5, 1)
w_avg = st.sidebar.slider("Avg sale per customer", 0, 5, 1)
w_mkt = st.sidebar.slider("Market size (est. consumers)", 0, 5, 1)
w_rent = st.sidebar.slider("Low rent per customer", 0, 5, 1)

sel_metrics = metrics if choice == "All" else metrics[metrics["city_name"] == choice]
sel_df = df if choice == "All" else df[df["city_name"] == choice]

# ---------------- Header + KPIs ----------------
st.title("☕ Monday Coffee: Expansion Dashboard")
st.caption("10,388 orders · 14 cities · Jan 2023 to Oct 2024")

rev, cx = sel_metrics["revenue"].sum(), sel_metrics["customers"].sum()
cols = st.columns(6)
cols[0].metric("Revenue", f"₹{rev:,.0f}")
cols[1].metric("Orders", f"{sel_metrics['orders'].sum():,}")
cols[2].metric("Customers", f"{cx:,}")
cols[3].metric("Avg sale per customer", f"₹{rev / cx:,.0f}")
cols[4].metric("Avg rent per customer", f"₹{sel_metrics['estimated_rent'].sum() / cx:,.0f}")
cols[5].metric("Est. coffee consumers", f"{sel_metrics['consumers_m'].sum():.2f}M")

# ---------------- Charts ----------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Revenue by city (₹)")
    plot = metrics.assign(highlight=metrics["city_name"].isin(PICKS if choice == "All" else [choice]))
    bar = (alt.Chart(plot).mark_bar().encode(
        x=alt.X("revenue:Q", title=None),
        y=alt.Y("city_name:N", sort="-x", title=None),
        color=alt.condition("datum.highlight", alt.value(ACCENT), alt.value(MUTED)),
        tooltip=["city_name", alt.Tooltip("revenue:Q", format=",.0f"), "customers"])
        .properties(height=360))
    st.altair_chart(bar, use_container_width=True)
    st.caption("Highlighted: Pune, Delhi, Jaipur (analyst picks)." if choice == "All"
               else f"Highlighted: {choice}.")

with c2:
    st.subheader(f"Monthly revenue (₹): {choice}")
    m = monthly_revenue(sel_df, exclude_partial)
    line = (alt.Chart(m).mark_line(point=True, color=ACCENT).encode(
        x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y")),
        y=alt.Y("revenue:Q", title=None),
        tooltip=[alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("revenue:Q", format=",.0f")])
        .properties(height=360))
    st.altair_chart(line, use_container_width=True)

st.subheader(f"Top 5 products by orders: {choice}")
tp = top_products(sel_df)
st.altair_chart(
    alt.Chart(tp).mark_bar(color=ACCENT).encode(
        x=alt.X("orders:Q", title=None), y=alt.Y("product_name:N", sort="-x", title=None),
        tooltip=["product_name", "orders"]).properties(height=220),
    use_container_width=True)

# ---------------- Expansion score ----------------
st.subheader("Expansion score")
scores = expansion_scores(metrics, w_rev, w_avg, w_mkt, w_rent)
top3 = ", ".join(scores["city_name"].head(3))
st.success(f"Top 3 with your weights: **{top3}**")

table = scores[["rank", "city_name", "score", "revenue", "customers",
                "avg_sale_per_cx", "rent_per_cx", "consumers_m"]].rename(columns={
    "rank": "Rank", "city_name": "City", "score": "Score", "revenue": "Revenue ₹",
    "customers": "Customers", "avg_sale_per_cx": "Avg sale ₹", "rent_per_cx": "Rent per cx ₹",
    "consumers_m": "Consumers (M)"})
styled = (table.style
          .format({"Score": "{:.2f}", "Revenue ₹": "{:,.0f}", "Avg sale ₹": "{:,.0f}",
                   "Rent per cx ₹": "{:,.0f}", "Consumers (M)": "{:.2f}"})
          .apply(lambda r: ["font-weight: bold; color: #b4571e" if r["City"] in PICKS else "" for _ in r],
                 axis=1))
st.dataframe(styled, use_container_width=True, hide_index=True)
st.caption("Each metric is scaled 0 to 1 across cities (rent is inverted). "
           "Analyst picks: Pune, Delhi, Jaipur. Chennai is the strong alternate and ranks above Jaipur at equal "
           "weights; raise the low-rent weight to see Jaipur climb.")
