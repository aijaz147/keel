"""
Exports flat, Looker-Studio-ready CSVs from the same order/session/ad-spend
data Keel runs on, using the same calculation functions in src/metrics.py --
so a number in Looker Studio and the same number in the Streamlit app will
always agree.

Run from the project root:
    python looker_studio/export_looker_data.py

Writes into looker_studio/data/:
    channel_daily.csv       -- date x channel x campaign, additive components only
    orders_detail.csv       -- order-line grain, for product/customer cuts
    product_summary.csv     -- one row per SKU
    cohort_retention.csv    -- cohort_month x month_index, long format

Design choice: these tables store additive raw components (net_revenue,
ad_spend, cogs, refunds, orders, new_customers, ...) rather than
pre-computed ratios. Ratios (ROAS, CAC, contribution margin) are built as
Looker Studio calculated fields on top -- SUM(a) / SUM(b) -- so they stay
correct under any date range or filter the report applies. Pre-computing a
ratio into a column and then averaging it across rows would silently break
as soon as someone changes the date filter.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import data_loader, metrics  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

raw = data_loader.load_raw()
orders = data_loader.build_orders_enriched()
ad_spend = raw["ad_spend"]

# ---------------------------------------------------------------------------
# 1. channel_daily.csv -- date x channel x campaign, additive components
# ---------------------------------------------------------------------------
o = orders.copy()
o["date"] = o["order_date"].dt.date
rev = o.groupby(["date", "channel", "campaign"]).apply(
    lambda g: pd.Series({
        "net_revenue": (g["gross_item_revenue"] - g["discount_amount"] + g["shipping_revenue"] + g["tax_amount"]).sum(),
        "cogs": g["cogs"].sum(),
        "shipping_cost": g["shipping_cost"].sum(),
        "payment_fees": g["payment_fee"].sum(),
        "refunds": g["refund_amount"].sum(),
        "orders": len(g),
        "new_customers": g.loc[g["is_new_customer"], "customer_id"].nunique(),
    }),
    include_groups=False,
).reset_index()

a = ad_spend.copy()
a["date"] = a["date"].dt.date
spend = a.groupby(["date", "channel", "campaign"]).agg(
    ad_spend=("spend", "sum"),
    platform_reported_revenue=("platform_reported_revenue", "sum"),
).reset_index()

channel_daily = pd.merge(rev, spend, on=["date", "channel", "campaign"], how="outer").fillna(0.0)
channel_daily = channel_daily.sort_values(["date", "channel", "campaign"])
channel_daily.to_csv(os.path.join(OUT_DIR, "channel_daily.csv"), index=False)
print(f"channel_daily.csv: {len(channel_daily):,} rows")

# ---------------------------------------------------------------------------
# 2. orders_detail.csv -- order-line grain
# ---------------------------------------------------------------------------
detail = orders.copy()
detail["net_item_revenue"] = detail["gross_item_revenue"] - detail["discount_amount"]
detail["net_revenue"] = detail["net_item_revenue"] + detail["shipping_revenue"] + detail["tax_amount"]
detail["customer_type"] = detail["is_new_customer"].map({True: "New", False: "Returning"})
detail_out = detail[[
    "order_id", "order_date", "channel", "campaign", "customer_type", "device", "region",
    "product_name", "category", "quantity", "unit_price", "gross_item_revenue", "discount_amount",
    "shipping_revenue", "tax_amount", "net_revenue", "cogs", "shipping_cost", "payment_fee",
    "refund_amount", "is_refunded",
]].rename(columns={"payment_fee": "payment_fees"})
detail_out.to_csv(os.path.join(OUT_DIR, "orders_detail.csv"), index=False)
print(f"orders_detail.csv: {len(detail_out):,} rows")

# ---------------------------------------------------------------------------
# 3. product_summary.csv -- reuses metrics.product_table for consistency
# ---------------------------------------------------------------------------
product_summary = metrics.product_table(orders)
product_summary.to_csv(os.path.join(OUT_DIR, "product_summary.csv"), index=False)
print(f"product_summary.csv: {len(product_summary):,} rows")

# ---------------------------------------------------------------------------
# 4. cohort_retention.csv -- reuses metrics.cohort_retention, long format
# ---------------------------------------------------------------------------
pivot = metrics.cohort_retention(orders)
cohort_long = pivot.reset_index().melt(id_vars="cohort_month", var_name="month_index", value_name="retention_pct")
cohort_long = cohort_long.dropna(subset=["retention_pct"])
# Kept as a raw 0-1 ratio (not x100) so it matches the convention of every
# other percent-like column in these exports -- set the Looker Studio field
# type to Percent and it formats itself, no calculated field needed.
cohort_long["retention_pct"] = cohort_long["retention_pct"].round(4)
cohort_long.to_csv(os.path.join(OUT_DIR, "cohort_retention.csv"), index=False)
print(f"cohort_retention.csv: {len(cohort_long):,} rows")

# ---------------------------------------------------------------------------
# 5. new_vs_returning_monthly.csv -- reuses metrics.new_vs_returning_trend
# ---------------------------------------------------------------------------
nvr = metrics.new_vs_returning_trend(orders)
nvr.to_csv(os.path.join(OUT_DIR, "new_vs_returning_monthly.csv"), index=False)
print(f"new_vs_returning_monthly.csv: {len(nvr):,} rows")

# ---------------------------------------------------------------------------
# 6. customer_summary.csv -- single-row headline stats, some metrics (repeat
#    purchase rate) require customer-grain logic Looker Studio can't derive
#    from order-line rows alone, so they're computed upstream here instead.
# ---------------------------------------------------------------------------
cs = metrics.customer_summary(orders)
pd.DataFrame([cs]).to_csv(os.path.join(OUT_DIR, "customer_summary.csv"), index=False)
print("customer_summary.csv: 1 row")

print("\nDone. Upload the CSVs in looker_studio/data/ to Looker Studio (File Upload connector")
print("or via Google Sheets) and follow looker_studio/BUILD_GUIDE.md.")
