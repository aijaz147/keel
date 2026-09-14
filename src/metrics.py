"""
KPI and business-logic calculations for Keel.

Every formula documented in README.md is implemented here and nowhere
else -- pages call into this module rather than recomputing metrics inline,
so the numbers stay consistent across the whole app.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def fmt_currency(v: float, decimals: int = 0) -> str:
    if pd.isna(v):
        return "$0"
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.{decimals}f}"


def fmt_pct(v: float, decimals: int = 1) -> str:
    if pd.isna(v):
        return "0.0%"
    return f"{v * 100:.{decimals}f}%"


def fmt_number(v: float, decimals: int = 0) -> str:
    if pd.isna(v):
        return "0"
    return f"{v:,.{decimals}f}"


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, None) or pd.isna(denominator):
        return 0.0
    return numerator / denominator


# ---------------------------------------------------------------------------
# Headline KPI summary
# ---------------------------------------------------------------------------
def kpi_summary(orders: pd.DataFrame, ad_spend: pd.DataFrame) -> dict:
    """Core financial KPIs for a filtered set of orders + matching ad spend.

    Definitions (see README for full detail):
      gross_revenue        = sum(unit_price * qty)                     [pre-discount product sales]
      net_revenue           = gross_revenue - discounts + shipping_rev + tax   [refunds NOT netted here]
      refunds                = sum(refund_amount) on these orders
      contribution_profit    = net_revenue - ad_spend - cogs - shipping_cost - payment_fees - refunds
      contribution_margin_pct = contribution_profit / net_revenue
      blended_roas / mer      = net_revenue / ad_spend
      cac                     = ad_spend / new_customers_acquired
    """
    n_orders = len(orders)
    gross_revenue = float(orders["gross_item_revenue"].sum())
    discounts = float(orders["discount_amount"].sum())
    shipping_revenue = float(orders["shipping_revenue"].sum())
    tax = float(orders["tax_amount"].sum())
    net_revenue = gross_revenue - discounts + shipping_revenue + tax

    refunds = float(orders["refund_amount"].sum()) if "refund_amount" in orders.columns else 0.0
    cogs = float(orders["cogs"].sum())
    shipping_cost = float(orders["shipping_cost"].sum())
    payment_fees = float(orders["payment_fee"].sum())
    ad_spend_total = float(ad_spend["spend"].sum())

    contribution_profit = net_revenue - ad_spend_total - cogs - shipping_cost - payment_fees - refunds
    contribution_margin_pct = safe_div(contribution_profit, net_revenue)

    blended_roas = safe_div(net_revenue, ad_spend_total)
    mer = blended_roas

    new_customers = int(orders.loc[orders["is_new_customer"], "customer_id"].nunique())
    cac = safe_div(ad_spend_total, new_customers)

    new_rev = float(orders.loc[orders["is_new_customer"], "net_item_revenue"].sum()) if "net_item_revenue" in orders.columns else 0.0
    ret_rev = float(orders.loc[~orders["is_new_customer"], "net_item_revenue"].sum()) if "net_item_revenue" in orders.columns else 0.0

    aov = safe_div(net_revenue, n_orders)
    profit_per_order = safe_div(contribution_profit, n_orders)
    refund_rate = safe_div(refunds, gross_revenue)

    return {
        "orders": n_orders,
        "gross_revenue": gross_revenue,
        "discounts": discounts,
        "shipping_revenue": shipping_revenue,
        "tax": tax,
        "net_revenue": net_revenue,
        "refunds": refunds,
        "refund_rate": refund_rate,
        "cogs": cogs,
        "shipping_cost": shipping_cost,
        "payment_fees": payment_fees,
        "ad_spend": ad_spend_total,
        "contribution_profit": contribution_profit,
        "contribution_margin_pct": contribution_margin_pct,
        "blended_roas": blended_roas,
        "mer": mer,
        "new_customers": new_customers,
        "cac": cac,
        "new_customer_revenue": new_rev,
        "returning_customer_revenue": ret_rev,
        "aov": aov,
        "profit_per_order": profit_per_order,
    }


def pct_delta(current: float, prior: float) -> tuple[float, bool | None]:
    """Returns (delta_pct, is_good) where is_good is None if prior==0."""
    if prior == 0:
        return (0.0, None)
    delta = (current - prior) / abs(prior)
    return (delta, delta >= 0)


# ---------------------------------------------------------------------------
# Trend series
# ---------------------------------------------------------------------------
def daily_trend(orders: pd.DataFrame, ad_spend: pd.DataFrame) -> pd.DataFrame:
    o = orders.copy()
    o["day"] = o["order_date"].dt.date
    daily_o = o.groupby("day").apply(
        lambda g: pd.Series({
            "net_revenue": (g["gross_item_revenue"] - g["discount_amount"] + g["shipping_revenue"] + g["tax_amount"]).sum(),
            "refunds": g["refund_amount"].sum(),
            "cogs": g["cogs"].sum(),
            "shipping_cost": g["shipping_cost"].sum(),
            "payment_fees": g["payment_fee"].sum(),
            "orders": len(g),
        }),
        include_groups=False,
    ).reset_index()

    a = ad_spend.copy()
    a["day"] = a["date"].dt.date
    daily_a = a.groupby("day")["spend"].sum().reset_index()

    merged = pd.merge(daily_o, daily_a, on="day", how="outer").fillna(0.0)
    merged = merged.sort_values("day")
    merged["contribution_profit"] = (
        merged["net_revenue"] - merged["spend"] - merged["cogs"] - merged["shipping_cost"]
        - merged["payment_fees"] - merged["refunds"]
    )
    merged = merged.rename(columns={"spend": "ad_spend"})
    return merged


# ---------------------------------------------------------------------------
# Channel performance
# ---------------------------------------------------------------------------
def channel_table(orders: pd.DataFrame, ad_spend: pd.DataFrame) -> pd.DataFrame:
    rev = orders.groupby("channel").apply(
        lambda g: pd.Series({
            "net_revenue": (g["gross_item_revenue"] - g["discount_amount"] + g["shipping_revenue"] + g["tax_amount"]).sum(),
            "refunds": g["refund_amount"].sum(),
            "cogs": g["cogs"].sum(),
            "shipping_cost": g["shipping_cost"].sum(),
            "payment_fees": g["payment_fee"].sum(),
            "orders": len(g),
            "new_customers": g.loc[g["is_new_customer"], "customer_id"].nunique(),
        }),
        include_groups=False,
    ).reset_index()

    spend = ad_spend.groupby("channel")["spend"].sum().reset_index().rename(columns={"spend": "ad_spend"})
    table = rev.merge(spend, on="channel", how="left")
    table["ad_spend"] = table["ad_spend"].fillna(0.0)

    table["contribution_profit"] = (
        table["net_revenue"] - table["ad_spend"] - table["cogs"] - table["shipping_cost"]
        - table["payment_fees"] - table["refunds"]
    )
    table["contribution_margin_pct"] = table["contribution_profit"] / table["net_revenue"].replace(0, np.nan)
    table["roas"] = table["net_revenue"] / table["ad_spend"].replace(0, np.nan)
    table["cac"] = table["ad_spend"] / table["new_customers"].replace(0, np.nan)
    table["aov"] = table["net_revenue"] / table["orders"].replace(0, np.nan)
    return table.sort_values("net_revenue", ascending=False).reset_index(drop=True)


def campaign_table(orders: pd.DataFrame, ad_spend: pd.DataFrame) -> pd.DataFrame:
    rev = orders.groupby(["channel", "campaign"]).apply(
        lambda g: pd.Series({
            "net_revenue": (g["gross_item_revenue"] - g["discount_amount"] + g["shipping_revenue"] + g["tax_amount"]).sum(),
            "refunds": g["refund_amount"].sum(),
            "cogs": g["cogs"].sum(),
            "shipping_cost": g["shipping_cost"].sum(),
            "payment_fees": g["payment_fee"].sum(),
            "orders": len(g),
            "new_customers": g.loc[g["is_new_customer"], "customer_id"].nunique(),
        }),
        include_groups=False,
    ).reset_index()

    spend = ad_spend.groupby(["channel", "campaign"]).agg(
        ad_spend=("spend", "sum"),
        platform_reported_revenue=("platform_reported_revenue", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
    ).reset_index()

    table = spend.merge(rev, on=["channel", "campaign"], how="left").fillna(0.0)
    table["contribution_profit"] = (
        table["net_revenue"] - table["ad_spend"] - table["cogs"] - table["shipping_cost"]
        - table["payment_fees"] - table["refunds"]
    )
    table["contribution_margin_pct"] = table["contribution_profit"] / table["net_revenue"].replace(0, np.nan)
    table["roas"] = table["net_revenue"] / table["ad_spend"].replace(0, np.nan)
    table["platform_roas"] = table["platform_reported_revenue"] / table["ad_spend"].replace(0, np.nan)
    table["cac"] = table["ad_spend"] / table["new_customers"].replace(0, np.nan)
    table["roas_profit_gap_flag"] = (table["roas"] >= 3) & (table["contribution_margin_pct"] < 0.15)
    return table.sort_values("ad_spend", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Product performance
# ---------------------------------------------------------------------------
def product_table(orders: pd.DataFrame) -> pd.DataFrame:
    o = orders.copy()
    o["net_revenue"] = o["gross_item_revenue"] - o["discount_amount"] + o["shipping_revenue"] + o["tax_amount"]
    o["is_paid"] = o["channel"].isin(["Google Ads", "Meta Ads"])

    g = o.groupby(["product_id", "product_name", "category"]).apply(
        lambda x: pd.Series({
            "units_sold": x["quantity"].sum(),
            "orders": len(x),
            "gross_item_revenue": x["gross_item_revenue"].sum(),
            "net_revenue": x["net_revenue"].sum(),
            "discount_amount": x["discount_amount"].sum(),
            "cogs": x["cogs"].sum(),
            "refunds": x["refund_amount"].sum(),
            "refund_orders": x["is_refunded"].sum(),
            "ad_attributed_revenue": x.loc[x["is_paid"], "net_revenue"].sum(),
        }),
        include_groups=False,
    ).reset_index()

    g["gross_margin"] = g["gross_item_revenue"] - g["cogs"]
    g["gross_margin_pct"] = g["gross_margin"] / g["gross_item_revenue"].replace(0, np.nan)
    g["discount_rate"] = g["discount_amount"] / g["gross_item_revenue"].replace(0, np.nan)
    g["refund_rate"] = g["refunds"] / g["gross_item_revenue"].replace(0, np.nan)
    # Contribution profit at the product-line level excludes shipping cost
    # and payment fees, which are not tracked per-SKU (they're order-level
    # costs) -- see README methodology notes.
    g["contribution_profit"] = g["net_revenue"] - g["cogs"] - g["refunds"]
    g["contribution_margin_pct"] = g["contribution_profit"] / g["net_revenue"].replace(0, np.nan)
    g["aov"] = g["net_revenue"] / g["orders"].replace(0, np.nan)
    return g.sort_values("net_revenue", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Customer metrics
# ---------------------------------------------------------------------------
def customer_summary(orders: pd.DataFrame) -> dict:
    n_customers = orders["customer_id"].nunique()
    order_counts = orders.groupby("customer_id").size()
    repeaters = (order_counts >= 2).sum()
    repeat_rate = safe_div(repeaters, n_customers)

    new_orders = orders[orders["is_new_customer"]]
    ret_orders = orders[~orders["is_new_customer"]]
    new_aov = safe_div(
        (new_orders["gross_item_revenue"] - new_orders["discount_amount"] + new_orders["shipping_revenue"] + new_orders["tax_amount"]).sum(),
        len(new_orders),
    )
    ret_aov = safe_div(
        (ret_orders["gross_item_revenue"] - ret_orders["discount_amount"] + ret_orders["shipping_revenue"] + ret_orders["tax_amount"]).sum(),
        len(ret_orders),
    )
    return {
        "customers": n_customers,
        "repeaters": int(repeaters),
        "repeat_rate": repeat_rate,
        "new_aov": new_aov,
        "returning_aov": ret_aov,
    }


def new_vs_returning_trend(orders: pd.DataFrame) -> pd.DataFrame:
    o = orders.copy()
    o["month"] = o["order_date"].dt.to_period("M").dt.to_timestamp()
    o["net_revenue"] = o["gross_item_revenue"] - o["discount_amount"] + o["shipping_revenue"] + o["tax_amount"]
    o["segment"] = np.where(o["is_new_customer"], "New", "Returning")
    return o.groupby(["month", "segment"])["net_revenue"].sum().reset_index()


def cohort_retention(orders_all: pd.DataFrame) -> pd.DataFrame:
    """Monthly acquisition-cohort retention matrix (% of cohort ordering in month N)."""
    o = orders_all.copy()
    first_order = o.groupby("customer_id")["order_date"].min().rename("cohort_date")
    o = o.merge(first_order, on="customer_id")
    o["cohort_month"] = o["cohort_date"].dt.to_period("M")
    o["order_month"] = o["order_date"].dt.to_period("M")
    o["month_index"] = (o["order_month"] - o["cohort_month"]).apply(lambda x: x.n)

    cohort_sizes = o[o["month_index"] == 0].groupby("cohort_month")["customer_id"].nunique()
    active = o.groupby(["cohort_month", "month_index"])["customer_id"].nunique().reset_index()
    active = active.merge(cohort_sizes.rename("cohort_size"), on="cohort_month")
    active["retention_pct"] = active["customer_id"] / active["cohort_size"]

    pivot = active.pivot(index="cohort_month", columns="month_index", values="retention_pct")
    pivot.index = pivot.index.astype(str)
    return pivot


def channel_quality_table(orders: pd.DataFrame) -> pd.DataFrame:
    """First-order contribution profit + repeat behavior by acquisition channel."""
    o = orders.copy()
    o["net_revenue"] = o["gross_item_revenue"] - o["discount_amount"] + o["shipping_revenue"] + o["tax_amount"]
    o["contribution_profit"] = o["net_revenue"] - o["cogs"] - o["shipping_cost"] - o["payment_fee"] - o["refund_amount"]

    first_orders = o[o["is_new_customer"]]
    acquisition_channel = first_orders.set_index("customer_id")["channel"]

    order_counts = o.groupby("customer_id").size()
    repeat_customers = set(order_counts[order_counts >= 2].index)

    rows = []
    for ch, grp in first_orders.groupby("channel"):
        cust_ids = grp["customer_id"].unique()
        n = len(cust_ids)
        repeat_n = len(set(cust_ids) & repeat_customers)
        rows.append({
            "channel": ch,
            "new_customers": n,
            "avg_first_order_contribution_profit": grp["contribution_profit"].mean(),
            "repeat_rate": safe_div(repeat_n, n),
        })
    return pd.DataFrame(rows).sort_values("new_customers", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Attribution modeling
# ---------------------------------------------------------------------------
ATTRIBUTION_MODELS = ["Last Click", "First Click", "Linear", "Data-Informed (proxy)"]


def _journey_touches(sessions: pd.DataFrame) -> pd.DataFrame:
    """Purchase-journey touches only (drops browse-only sessions and dedupes
    duplicate purchase-event fires by journey_id)."""
    j = sessions[sessions["journey_id"].notna()].copy()
    j = j.sort_values(["journey_id", "touch_position"])
    j = j.drop_duplicates(subset=["journey_id", "touch_position"], keep="first")
    return j


def attributed_revenue_by_channel(sessions: pd.DataFrame, orders: pd.DataFrame, model: str) -> pd.DataFrame:
    """Revenue by channel under a given attribution model, using multi-touch
    journeys reconstructed from web_sessions. Orders with no session match at
    all fall into an 'Unattributed' bucket regardless of model."""
    touches = _journey_touches(sessions)
    order_rev = orders.set_index("order_id")["gross_revenue"] if "gross_revenue" in orders.columns else orders.set_index("order_id")["net_revenue"]

    matched_order_ids = set(touches["journey_id"].unique())
    all_order_ids = set(orders["order_id"].unique())
    unmatched_ids = all_order_ids - matched_order_ids
    unattributed_revenue = float(order_rev.reindex(list(unmatched_ids)).fillna(0).sum())

    credit_rows = []
    for journey_id, grp in touches.groupby("journey_id"):
        if journey_id not in order_rev.index:
            continue
        rev = float(order_rev.loc[journey_id])
        grp = grp.sort_values("touch_position")
        channels = grp["source"].tolist()
        n = len(channels)

        if model == "Last Click":
            weights = [0.0] * (n - 1) + [1.0]
        elif model == "First Click":
            weights = [1.0] + [0.0] * (n - 1)
        elif model == "Linear":
            weights = [1.0 / n] * n
        else:  # Data-Informed proxy: U-shaped 40/20/40
            if n == 1:
                weights = [1.0]
            elif n == 2:
                weights = [0.5, 0.5]
            else:
                mid = n - 2
                weights = [0.4] + [0.2 / mid] * mid + [0.4]

        for ch, w in zip(channels, weights):
            if w > 0:
                credit_rows.append({"channel": ch, "revenue": rev * w})

    if credit_rows:
        result = pd.DataFrame(credit_rows).groupby("channel")["revenue"].sum().reset_index()
    else:
        result = pd.DataFrame(columns=["channel", "revenue"])

    result = pd.concat([result, pd.DataFrame([{"channel": "Unattributed", "revenue": unattributed_revenue}])], ignore_index=True)
    result = result.groupby("channel")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
    return result.reset_index(drop=True)


def revenue_reconciliation(orders: pd.DataFrame, sessions: pd.DataFrame, ad_spend: pd.DataFrame) -> dict:
    """Three revenue figures for the SAME paid-channel scope (Google Ads +
    Meta Ads), so the comparison is apples-to-apples. Ad platforms only ever
    report revenue for the campaigns they served, so comparing them against
    total store revenue (which includes organic/email/direct) would always
    make the platform figure look artificially small regardless of any
    genuine over- or under-reporting -- scoping all three to paid channels is
    what actually isolates the platform-inflation signal."""
    paid_channels = ["Google Ads", "Meta Ads"]
    paid_orders = orders[orders["channel"].isin(paid_channels)]
    order_system_revenue = float(paid_orders["gross_revenue"].sum())

    purchase_sessions = sessions[sessions["is_purchase"]].drop_duplicates(subset=["transaction_id"], keep="first")
    paid_purchase_sessions = purchase_sessions[purchase_sessions["source"].isin(paid_channels)]
    ga4_revenue = float(paid_purchase_sessions["revenue_ga4"].sum())

    platform_revenue = float(ad_spend["platform_reported_revenue"].sum())

    return {
        "order_system_revenue": order_system_revenue,
        "ga4_tracked_revenue": ga4_revenue,
        "ad_platform_attributed_revenue": platform_revenue,
    }


def funnel_metrics(sessions: pd.DataFrame) -> pd.DataFrame:
    stages = [
        ("Sessions", len(sessions)),
        ("Product Views", int(sessions["viewed_product"].sum())),
        ("Add to Cart", int(sessions["added_to_cart"].sum())),
        ("Checkout Started", int(sessions["began_checkout"].sum())),
        ("Purchase", int(sessions["is_purchase"].sum())),
    ]
    df = pd.DataFrame(stages, columns=["stage", "count"])
    df["conversion_from_prev"] = df["count"] / df["count"].shift(1)
    df["conversion_from_first"] = df["count"] / df["count"].iloc[0]
    return df


def tracking_health(orders: pd.DataFrame, sessions: pd.DataFrame) -> dict:
    n_orders = len(orders)
    matched_order_ids = set(sessions.loc[sessions["is_purchase"], "transaction_id"].dropna().unique())
    unattributed_orders = orders[~orders["order_id"].isin(matched_order_ids)]
    unattributed_rate = safe_div(len(unattributed_orders), n_orders)

    paid_sessions = sessions[sessions["source"].isin(["Google Ads", "Meta Ads", "Organic Social"])]
    missing_utm = paid_sessions["utm_campaign"].isna()
    missing_utm_rate = safe_div(missing_utm.sum(), len(paid_sessions))

    purchase_sessions = sessions[sessions["is_purchase"]]
    dup_counts = purchase_sessions.groupby("transaction_id").size()
    duplicate_txns = dup_counts[dup_counts > 1]
    duplicate_rate = safe_div(duplicate_txns.sum() - len(duplicate_txns), len(purchase_sessions))

    matched = purchase_sessions.drop_duplicates(subset=["transaction_id"], keep="first")
    order_rev_lookup = orders.set_index("order_id")["gross_revenue"]
    matched = matched[matched["transaction_id"].isin(order_rev_lookup.index)]
    order_rev = matched["transaction_id"].map(order_rev_lookup)
    mismatch = (order_rev - matched["revenue_ga4"]).abs() > 0.5
    revenue_mismatch_rate = safe_div(mismatch.sum(), len(matched)) if len(matched) else 0.0

    missing_campaign_rate = safe_div(len(orders[orders["channel"] == "Unattributed"]), n_orders)

    issue_rates = {
        "Missing UTMs on paid sessions": missing_utm_rate,
        "Duplicate purchase events": duplicate_rate,
        "GA4 vs. order revenue mismatches": revenue_mismatch_rate,
        "Unattributed orders (no session match)": unattributed_rate,
        "Orders missing campaign value": missing_campaign_rate,
    }

    score = 100.0
    score -= missing_utm_rate * 25
    score -= duplicate_rate * 20
    score -= revenue_mismatch_rate * 20
    score -= unattributed_rate * 25
    score -= missing_campaign_rate * 10
    score = max(0.0, min(100.0, score))

    return {"score": score, "issues": issue_rates}
