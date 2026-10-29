"""Data logic for the Monday Coffee dashboard (pure pandas, no Streamlit)."""
from pathlib import Path
import pandas as pd

PICKS = ["Pune", "Delhi", "Jaipur"]          # analyst recommendation
PARTIAL_MONTH_START = pd.Timestamp("2024-10-01")  # data stops on 2024-10-01 (8 sales)


def load_data(data_dir):
    d = Path(data_dir)
    city = pd.read_csv(d / "city.csv")
    customers = pd.read_csv(d / "customers.csv")
    products = pd.read_csv(d / "products.csv")
    sales = pd.read_csv(d / "sales.csv", parse_dates=["sale_date"])
    df = (sales.merge(customers, on="customer_id")
               .merge(city, on="city_id")
               .merge(products, on="product_id"))
    return city, df


def city_metrics(city, df):
    g = (df.groupby("city_name")
           .agg(revenue=("total", "sum"), orders=("sale_id", "count"),
                customers=("customer_id", "nunique"))
           .reset_index()
           .merge(city[["city_name", "estimated_rent", "population"]], on="city_name"))
    g["avg_sale_per_cx"] = g["revenue"] / g["customers"]
    g["rent_per_cx"] = g["estimated_rent"] / g["customers"]
    g["consumers_m"] = g["population"] * 0.25 / 1e6
    return g


def _minmax(s):
    return (s - s.min()) / (s.max() - s.min())


def expansion_scores(g, w_rev=1, w_avg=1, w_mkt=1, w_rent=1):
    """Weighted min-max score (0-1). Lower rent per customer is better."""
    out = g.copy()
    total = (w_rev + w_avg + w_mkt + w_rent) or 1
    out["score"] = (w_rev * _minmax(out["revenue"])
                    + w_avg * _minmax(out["avg_sale_per_cx"])
                    + w_mkt * _minmax(out["consumers_m"])
                    + w_rent * (1 - _minmax(out["rent_per_cx"]))) / total
    out["rank"] = out["score"].rank(ascending=False, method="min").astype(int)
    return out.sort_values(["rank", "revenue"], ascending=[True, False]).reset_index(drop=True)


def monthly_revenue(df, exclude_partial=True):
    d = df[df["sale_date"] < PARTIAL_MONTH_START] if exclude_partial else df
    m = d.assign(month=d["sale_date"].dt.to_period("M").dt.to_timestamp())
    return m.groupby("month", as_index=False)["total"].sum().rename(columns={"total": "revenue"})


def top_products(df, n=5):
    return (df.groupby("product_name").size().sort_values(ascending=False)
              .head(n).rename("orders").reset_index())
