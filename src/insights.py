"""
Key Insights engine.

Every insight returned here is computed from the *actual filtered
DataFrames* passed in -- nothing is a hard-coded string. Each function
returns a list of dicts: {"text": str, "kind": "good"|"warn"|"bad"|"neutral"}.
"""

from __future__ import annotations

import pandas as pd

from src.metrics import fmt_currency, fmt_pct, safe_div


def executive_insights(
    kpis: dict,
    prior_kpis: dict | None,
    channel_df: pd.DataFrame,
    campaign_df: pd.DataFrame,
    customer_summary: dict,
) -> list[dict]:
    out: list[dict] = []

    # 1. Overall trajectory
    if prior_kpis and prior_kpis["net_revenue"] > 0:
        rev_delta = safe_div(kpis["net_revenue"] - prior_kpis["net_revenue"], prior_kpis["net_revenue"])
        margin_delta_pts = (kpis["contribution_margin_pct"] - prior_kpis["contribution_margin_pct"]) * 100
        direction = "grew" if rev_delta >= 0 else "declined"
        kind = "good" if rev_delta >= 0 else "bad"
        out.append({
            "text": (
                f"Net revenue {direction} {abs(rev_delta) * 100:.1f}% vs. the prior period to "
                f"{fmt_currency(kpis['net_revenue'])}, while contribution margin moved "
                f"{margin_delta_pts:+.1f} points to {fmt_pct(kpis['contribution_margin_pct'])}."
            ),
            "kind": kind,
        })

    # 2. Channel revenue share vs. margin risk (paid channels only)
    paid = channel_df[channel_df["ad_spend"] > 0].copy()
    if not paid.empty:
        total_paid_rev = paid["net_revenue"].sum()
        paid["rev_share"] = paid["net_revenue"] / total_paid_rev if total_paid_rev else 0
        top = paid.sort_values("net_revenue", ascending=False).iloc[0]
        if top["rev_share"] >= 0.3 and top["contribution_margin_pct"] < 0.18:
            out.append({
                "text": (
                    f"{top['channel']} generated {fmt_pct(top['rev_share'])} of paid-channel revenue but "
                    f"contribution margin sits at just {fmt_pct(top['contribution_margin_pct'])} "
                    f"(CAC: {fmt_currency(top['cac'], 2)}) -- a concentration risk if acquisition costs keep rising."
                ),
                "kind": "warn",
            })
        elif top["rev_share"] >= 0.3:
            out.append({
                "text": (
                    f"{top['channel']} is the leading paid channel at {fmt_pct(top['rev_share'])} of paid revenue "
                    f"with a healthy {fmt_pct(top['contribution_margin_pct'])} contribution margin."
                ),
                "kind": "good",
            })

    # 3. Campaign ROAS vs. contribution profit conflict
    flagged = campaign_df[(campaign_df["roas"] >= 3) & (campaign_df["contribution_profit"] < 0)]
    if not flagged.empty:
        worst = flagged.sort_values("contribution_profit").iloc[0]
        out.append({
            "text": (
                f"Campaign \"{worst['campaign']}\" ({worst['channel']}) shows a {worst['roas']:.1f}x ROAS but a "
                f"negative contribution profit of {fmt_currency(worst['contribution_profit'])} once product cost, "
                f"fulfillment, fees, and refunds are counted."
            ),
            "kind": "bad",
        })

    # 4. Returning customer contribution
    ret_share = safe_div(kpis["returning_customer_revenue"], kpis["net_revenue"])
    if ret_share > 0:
        out.append({
            "text": (
                f"Returning customers account for {fmt_pct(ret_share)} of net revenue "
                f"({fmt_currency(kpis['returning_customer_revenue'])}) while requiring no incremental "
                f"acquisition spend -- a {fmt_pct(customer_summary['repeat_rate'])} repeat purchase rate overall."
            ),
            "kind": "good",
        })

    # 5. Overall profitability read
    if kpis["contribution_margin_pct"] < 0.15:
        out.append({
            "text": (
                f"Blended contribution margin is {fmt_pct(kpis['contribution_margin_pct'])} against a "
                f"{kpis['blended_roas']:.1f}x blended ROAS -- ad efficiency looks fine on platform metrics alone, "
                f"but landed profitability is thin once COGS, fulfillment, fees, and refunds are included."
            ),
            "kind": "warn",
        })
    else:
        out.append({
            "text": (
                f"Contribution margin is a healthy {fmt_pct(kpis['contribution_margin_pct'])} "
                f"({fmt_currency(kpis['contribution_profit'])} in contribution profit) at a {kpis['blended_roas']:.1f}x blended ROAS."
            ),
            "kind": "good",
        })

    return out[:5]


def next_look_recommendations(
    campaign_df: pd.DataFrame,
    product_df: pd.DataFrame,
    tracking: dict,
    channel_df: pd.DataFrame,
) -> list[str]:
    recos: list[str] = []

    flagged = campaign_df[(campaign_df["roas"] >= 3) & (campaign_df["contribution_margin_pct"] < 0.15)]
    if not flagged.empty:
        names = ", ".join(flagged.sort_values("ad_spend", ascending=False)["campaign"].head(2).tolist())
        recos.append(f"Audit contribution margin (not just ROAS) on: {names} -- open Paid Media Performance.")

    weak_products = product_df[(product_df["net_revenue"] > product_df["net_revenue"].median()) & (product_df["contribution_margin_pct"] < 0.15)]
    if not weak_products.empty:
        names = ", ".join(weak_products.sort_values("net_revenue", ascending=False)["product_name"].head(2).tolist())
        recos.append(f"Revenue-heavy but margin-thin SKUs to review: {names} -- open Product & Profitability.")

    if tracking["score"] < 85:
        worst_issue = max(tracking["issues"], key=tracking["issues"].get)
        recos.append(
            f"Tracking health score is {tracking['score']:.0f}/100, driven mainly by \"{worst_issue}\" "
            f"({fmt_pct(tracking['issues'][worst_issue])}) -- open Attribution & Tracking Health."
        )

    low_margin_channels = channel_df[(channel_df["ad_spend"] > 0) & (channel_df["contribution_margin_pct"] < 0.1)]
    if not low_margin_channels.empty:
        names = ", ".join(low_margin_channels["channel"].tolist())
        recos.append(f"{names} are running below 10% contribution margin -- reassess budget allocation on Paid Media Performance.")

    if not recos:
        recos.append("No urgent flags in the current filter selection -- performance looks broadly healthy across channels and products.")

    return recos[:5]


def paid_media_commentary(campaign_df: pd.DataFrame) -> str:
    strong_roas_weak_margin = campaign_df[(campaign_df["roas"] >= 3) & (campaign_df["contribution_margin_pct"] < 0.15)]
    unprofitable = campaign_df[campaign_df["contribution_profit"] < 0]
    n_total = len(campaign_df)

    if strong_roas_weak_margin.empty and unprofitable.empty:
        return (
            "Every active campaign in this view clears both a healthy ROAS and a healthy contribution margin -- "
            "platform-reported efficiency and landed profitability agree here."
        )

    parts = []
    if not strong_roas_weak_margin.empty:
        share = safe_div(strong_roas_weak_margin["ad_spend"].sum(), campaign_df["ad_spend"].sum())
        parts.append(
            f"{len(strong_roas_weak_margin)} of {n_total} campaigns ({fmt_pct(share)} of spend in view) post a strong "
            f"platform ROAS (3x+) but a contribution margin under 15% once COGS, shipping, payment fees, and refunds are applied."
        )
    if not unprofitable.empty:
        worst = unprofitable.sort_values("contribution_profit").iloc[0]
        parts.append(
            f"{len(unprofitable)} campaign(s) are outright unprofitable on a contribution basis -- worst is "
            f"\"{worst['campaign']}\" at {fmt_currency(worst['contribution_profit'])}, despite a {worst['roas']:.1f}x ROAS."
        )
    parts.append(
        "Platform ROAS reflects ad efficiency against revenue -- it says nothing about product cost, fulfillment "
        "cost, or refund exposure, so a scaling decision based on ROAS alone can quietly fund unprofitable growth."
    )
    return " ".join(parts)


def customer_quality_commentary(channel_quality_df: pd.DataFrame) -> str:
    if channel_quality_df.empty:
        return "Not enough data in the current filter to compare channel quality."
    best = channel_quality_df.sort_values("avg_first_order_contribution_profit", ascending=False).iloc[0]
    worst = channel_quality_df.sort_values("avg_first_order_contribution_profit", ascending=True).iloc[0]
    return (
        f"CAC alone doesn't tell you whether an acquisition channel is a good investment. "
        f"{best['channel']} customers average {fmt_currency(best['avg_first_order_contribution_profit'])} contribution "
        f"profit on their first order with a {fmt_pct(best['repeat_rate'])} repeat rate, while {worst['channel']} "
        f"customers average {fmt_currency(worst['avg_first_order_contribution_profit'])} with a "
        f"{fmt_pct(worst['repeat_rate'])} repeat rate -- evaluate acquisition spend against downstream quality, not CAC in isolation."
    )
