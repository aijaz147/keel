"""
Keel -- E-commerce Profit & Attribution Command Center
================================================================
An analytics application for e-commerce profit, marketing attribution,
and tracking health (GA4, GTM, SQL, Looker Studio / Power BI, PPC
attribution).

Run:
    streamlit run app.py
"""

from __future__ import annotations

import duckdb
import pandas as pd
import streamlit as st

from src import charts, data_loader, insights, metrics
from src.data_loader import Filters
from src.styles import brand_lockup, inject_global_css, metric_card, multi_stat_card, section_title, tag_strip

st.set_page_config(
    page_title="Keel | Luma Skin Command Center",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ---------------------------------------------------------------------------
# Load data once (cached)
# ---------------------------------------------------------------------------
raw = data_loader.load_raw()
orders_all = data_loader.build_orders_enriched()
customers_all = raw["customers"]
ad_spend_all = raw["ad_spend"]
sessions_all = raw["web_sessions"]
products_all = raw["products"]
refunds_all = raw["refunds"]

MIN_DATE, MAX_DATE = data_loader.date_bounds()

# ---------------------------------------------------------------------------
# Sidebar: navigation + global filters
# ---------------------------------------------------------------------------
with st.sidebar:
    brand_lockup("Keel", "LUMA SKIN &middot; COMMAND CENTER")
    st.write("")

    page = st.radio(
        "Navigate",
        [
            "Executive Overview",
            "Paid Media Performance",
            "Product & Profitability",
            "Customer & Retention",
            "Attribution & Tracking Health",
            "Data Explorer",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**Global Filters**")

    date_range = st.date_input(
        "Date range",
        value=(MAX_DATE - pd.Timedelta(days=89), MAX_DATE),
        min_value=MIN_DATE,
        max_value=MAX_DATE,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = MIN_DATE, MAX_DATE

    compare_enabled = st.checkbox("Compare to prior period", value=True)

    all_channels = sorted(orders_all["channel"].unique().tolist())
    sel_channels = st.multiselect("Channel", all_channels, default=[])

    customer_type = st.radio("Customer type", ["All", "New", "Returning"], horizontal=True)

    all_devices = sorted(orders_all["device"].unique().tolist())
    sel_devices = st.multiselect("Device", all_devices, default=[])

f = Filters(
    start_date=start_date, end_date=end_date, channels=sel_channels,
    customer_type=customer_type, device=sel_devices,
)

orders_f = data_loader.filter_orders(orders_all, f)
ad_spend_f = data_loader.filter_ad_spend(ad_spend_all, f)
sessions_f = data_loader.filter_sessions(sessions_all, f)

prior_kpis = None
if compare_enabled:
    f_prior = data_loader.comparison_window(f)
    orders_prior = data_loader.filter_orders(orders_all, f_prior)
    ad_spend_prior = data_loader.filter_ad_spend(ad_spend_all, f_prior)
    if len(orders_prior) > 0:
        prior_kpis = metrics.kpi_summary(orders_prior, ad_spend_prior)

def empty_state(msg: str = "No data matches the current filters. Try widening the date range or clearing filters.") -> None:
    st.info(msg)


# ===========================================================================
# PAGE: Executive Overview
# ===========================================================================
def page_executive_overview() -> None:
    st.title("Luma Skin Performance Command Center")
    st.caption(
        f"Showing **{f.start_date:%b %d, %Y}** to **{f.end_date:%b %d, %Y}**"
        + (f"  &middot;  compared to **{f_prior.start_date:%b %d} - {f_prior.end_date:%b %d, %Y}**" if compare_enabled and prior_kpis else "")
    )
    tag_strip(["SHOPIFY", "GA4", "GOOGLE ADS", "META ADS"])

    if orders_f.empty:
        empty_state()
        return

    kpis = metrics.kpi_summary(orders_f, ad_spend_f)

    def delta_str(key, is_pct_points=False, higher_is_better=True):
        if not prior_kpis:
            return None, None
        cur, prev = kpis[key], prior_kpis[key]
        if is_pct_points:
            diff = (cur - prev) * 100
            good = diff >= 0 if higher_is_better else diff <= 0
            return f"{diff:+.1f} pts vs prior", good
        d, good = metrics.pct_delta(cur, prev)
        if not higher_is_better and good is not None:
            good = not good
        return f"{d * 100:+.1f}% vs prior", good

    specs = [
        ("Net Revenue", metrics.fmt_currency(kpis["net_revenue"]), "net_revenue", False, True),
        ("Ad Spend", metrics.fmt_currency(kpis["ad_spend"]), "ad_spend", False, False),
        ("Contribution Profit", metrics.fmt_currency(kpis["contribution_profit"]), "contribution_profit", False, True),
        ("Contribution Margin", metrics.fmt_pct(kpis["contribution_margin_pct"]), "contribution_margin_pct", True, True),
        ("MER (Net Rev / Spend)", f"{kpis['mer']:.2f}x", "mer", False, True),
        ("CAC", metrics.fmt_currency(kpis["cac"], 2), "cac", False, False),
    ]
    row1, row2 = st.columns(3), st.columns(3)
    for col, (label, value, key, is_pts, higher_better) in zip(row1 + row2, specs):
        d, good = delta_str(key, is_pts, higher_better)
        with col:
            st.markdown(metric_card(label, value, d, good), unsafe_allow_html=True)

    st.write("")
    section_title("Revenue, Spend & Contribution Profit Trend")
    trend = metrics.daily_trend(orders_f, ad_spend_f)
    st.plotly_chart(charts.revenue_spend_profit_trend(trend), use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([1.6, 1])
    with left:
        section_title("Channel Performance", "Revenue, spend, ROAS, CAC, and contribution profit by channel")
        ch_table = metrics.channel_table(orders_f, ad_spend_f)
        display = ch_table.copy()
        display["net_revenue"] = display["net_revenue"].map(lambda v: metrics.fmt_currency(v))
        display["ad_spend"] = display["ad_spend"].map(lambda v: metrics.fmt_currency(v))
        display["roas"] = display["roas"].map(lambda v: f"{v:.2f}x" if pd.notna(v) else "—")
        display["cac"] = display["cac"].map(lambda v: metrics.fmt_currency(v, 2) if pd.notna(v) else "—")
        display["contribution_profit"] = display["contribution_profit"].map(lambda v: metrics.fmt_currency(v))
        display["contribution_margin_pct"] = display["contribution_margin_pct"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
        display = display.rename(columns={
            "channel": "Channel", "net_revenue": "Net Revenue", "ad_spend": "Ad Spend", "roas": "ROAS",
            "cac": "CAC", "contribution_profit": "Contribution Profit", "contribution_margin_pct": "Contribution Margin",
            "orders": "Orders", "new_customers": "New Customers",
        })
        st.dataframe(
            display[["Channel", "Net Revenue", "Ad Spend", "ROAS", "CAC", "Contribution Profit", "Contribution Margin", "Orders", "New Customers"]],
            use_container_width=True, hide_index=True,
        )
    with right:
        section_title("Revenue Mix by Channel")
        st.plotly_chart(charts.revenue_mix_donut(ch_table), use_container_width=True, config={"displayModeBar": False})

    section_title("New vs. Returning Customer Revenue")
    nvr = metrics.new_vs_returning_trend(orders_f)
    st.plotly_chart(charts.new_vs_returning_bar(nvr), use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns(2)
    campaign_df = metrics.campaign_table(orders_f, ad_spend_f)
    cust_summary = metrics.customer_summary(orders_f)
    with left:
        section_title("Key Insights", "Automatically generated from the current filter selection")
        for ins in insights.executive_insights(kpis, prior_kpis, ch_table, campaign_df, cust_summary):
            cls = {"good": "good", "warn": "warn", "bad": "bad"}.get(ins["kind"], "")
            st.markdown(f'<div class="pp-insight {cls}">{ins["text"]}</div>', unsafe_allow_html=True)
    with right:
        section_title("Where Should I Look Next?", "Actionable follow-ups based on this data")
        tracking = metrics.tracking_health(orders_f, sessions_f)
        product_df = metrics.product_table(orders_f)
        for reco in insights.next_look_recommendations(campaign_df, product_df, tracking, ch_table):
            st.markdown(f'<div class="pp-reco">&rarr; {reco}</div>', unsafe_allow_html=True)

    with st.expander("Methodology: how these numbers are calculated"):
        st.markdown(
            """
- **Net Revenue** = Gross product revenue − discounts + shipping revenue + tax collected (refunds are *not* netted here; see below).
- **Contribution Profit** = Net Revenue − Ad Spend − COGS − Shipping Cost − Payment Fees − Refunds.
- **Blended ROAS / MER** = Net Revenue ÷ Total Ad Spend across all channels (organic/direct/email carry $0 spend).
- **CAC** = Ad Spend ÷ new customers acquired in the period.
- Full metric definitions are documented in `README.md`.
            """
        )


# ===========================================================================
# PAGE: Paid Media Performance
# ===========================================================================
def page_paid_media() -> None:
    st.title("Paid Media Performance")
    st.caption("Google Ads and Meta Ads efficiency, reconciled against landed contribution profit.")

    paid_orders_all = orders_f[orders_f["channel"].isin(["Google Ads", "Meta Ads"])]
    if paid_orders_all.empty or ad_spend_f.empty:
        empty_state("No paid-channel data in the current filter selection.")
        return

    all_campaigns = sorted(ad_spend_f["campaign"].unique().tolist())
    c1, c2 = st.columns([2, 1])
    with c1:
        sel_campaigns = st.multiselect("Campaign filter (this page)", all_campaigns, default=[])
    with c2:
        sel_platform = st.multiselect("Platform", ["Google Ads", "Meta Ads"], default=[])

    p_orders = paid_orders_all.copy()
    p_spend = ad_spend_f[ad_spend_f["channel"].isin(["Google Ads", "Meta Ads"])].copy()
    if sel_campaigns:
        p_orders = p_orders[p_orders["campaign"].isin(sel_campaigns)]
        p_spend = p_spend[p_spend["campaign"].isin(sel_campaigns)]
    if sel_platform:
        p_orders = p_orders[p_orders["channel"].isin(sel_platform)]
        p_spend = p_spend[p_spend["channel"].isin(sel_platform)]

    if p_orders.empty or p_spend.empty:
        empty_state("No data for this campaign/platform combination.")
        return

    campaign_df = metrics.campaign_table(p_orders, p_spend)

    section_title("Google Ads vs. Meta Ads")
    ch_summary = metrics.channel_table(p_orders, p_spend)
    gc, mc = st.columns(2)
    for col, chan in zip([gc, mc], ["Google Ads", "Meta Ads"]):
        row = ch_summary[ch_summary["channel"] == chan]
        with col:
            if row.empty:
                st.markdown(metric_card(chan, "No data"), unsafe_allow_html=True)
                continue
            r = row.iloc[0]
            stats = [
                ("Net Revenue", metrics.fmt_currency(r["net_revenue"])),
                ("ROAS", f"{r['roas']:.2f}x" if pd.notna(r["roas"]) else "—"),
                ("Margin", metrics.fmt_pct(r["contribution_margin_pct"]) if pd.notna(r["contribution_margin_pct"]) else "—"),
            ]
            subtitle = f"CAC {metrics.fmt_currency(r['cac'], 2) if pd.notna(r['cac']) else '—'} &middot; {int(r['new_customers'])} new customers"
            st.markdown(multi_stat_card(chan, subtitle, stats), unsafe_allow_html=True)

    section_title("Campaign-Level Performance")
    display = campaign_df.copy()
    for c in ["ad_spend", "net_revenue", "cogs", "contribution_profit"]:
        display[c] = display[c].map(metrics.fmt_currency)
    display["roas"] = campaign_df["roas"].map(lambda v: f"{v:.2f}x" if pd.notna(v) else "—")
    display["cac"] = campaign_df["cac"].map(lambda v: metrics.fmt_currency(v, 2) if pd.notna(v) else "—")
    display["contribution_margin_pct"] = campaign_df["contribution_margin_pct"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
    display["Flag"] = campaign_df["roas_profit_gap_flag"].map(lambda v: "⚠ ROAS strong, margin weak" if v else "")
    display = display.rename(columns={
        "channel": "Channel", "campaign": "Campaign", "ad_spend": "Spend", "net_revenue": "Attributed Revenue",
        "roas": "ROAS", "cac": "CAC", "new_customers": "New Customers",
        "contribution_profit": "Contribution Profit", "contribution_margin_pct": "Contribution Margin",
    })
    st.dataframe(
        display[["Channel", "Campaign", "Spend", "Attributed Revenue", "ROAS", "CAC", "New Customers", "Contribution Profit", "Contribution Margin", "Flag"]],
        use_container_width=True, hide_index=True,
    )

    left, right = st.columns(2)
    with left:
        section_title("ROAS vs. Contribution Margin", "Bubble size = spend. Bottom-right quadrant = high ROAS, weak margin.")
        st.plotly_chart(charts.roas_margin_scatter(campaign_df), use_container_width=True, config={"displayModeBar": False})
    with right:
        section_title("Spend & ROAS Trend")
        daily = p_orders.copy()
        daily["day"] = daily["order_date"].dt.date
        daily_rev = daily.groupby("day")["net_revenue"].sum().reset_index()
        daily_spend = p_spend.copy()
        daily_spend["day"] = daily_spend["date"].dt.date
        daily_spend = daily_spend.groupby("day")["spend"].sum().reset_index()
        trend = pd.merge(daily_rev, daily_spend, on="day", how="outer").fillna(0).sort_values("day")
        trend = trend.rename(columns={"spend": "ad_spend"})
        trend["roas"] = trend["net_revenue"] / trend["ad_spend"].replace(0, pd.NA)
        st.plotly_chart(charts.spend_roas_cac_trend(trend), use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f'<div class="pp-insight warn"><b>Analyst note:</b> {insights.paid_media_commentary(campaign_df)}</div>',
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE: Product & Profitability
# ===========================================================================
def page_product_profitability() -> None:
    st.title("Product & Profitability")
    st.caption("SKU-level revenue, margin, and the products that dilute profit despite strong sales.")

    if orders_f.empty:
        empty_state()
        return

    product_df = metrics.product_table(orders_f)

    section_title("Product Performance")
    display = product_df.copy()
    for c in ["net_revenue", "cogs", "ad_attributed_revenue", "contribution_profit"]:
        display[c] = display[c].map(metrics.fmt_currency)
    display["gross_margin_pct"] = product_df["gross_margin_pct"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
    display["discount_rate"] = product_df["discount_rate"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
    display["refund_rate"] = product_df["refund_rate"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
    display["contribution_margin_pct"] = product_df["contribution_margin_pct"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
    display = display.rename(columns={
        "product_name": "Product", "category": "Category", "units_sold": "Units Sold",
        "net_revenue": "Net Revenue", "cogs": "COGS", "discount_rate": "Discount Rate",
        "refund_rate": "Refund Rate", "gross_margin_pct": "Gross Margin %",
        "ad_attributed_revenue": "Ad-Attributed Revenue", "contribution_profit": "Contribution Profit",
        "contribution_margin_pct": "Contribution Margin",
    })
    st.dataframe(
        display[["Product", "Category", "Units Sold", "Net Revenue", "COGS", "Discount Rate", "Refund Rate",
                  "Gross Margin %", "Ad-Attributed Revenue", "Contribution Profit", "Contribution Margin"]],
        use_container_width=True, hide_index=True,
    )

    left, right = st.columns(2)
    with left:
        section_title("Product Margin Ranking")
        st.plotly_chart(charts.product_margin_rank(product_df), use_container_width=True, config={"displayModeBar": False})
    with right:
        section_title("Revenue vs. Contribution Margin", "Bubble size = units sold")
        st.plotly_chart(charts.product_revenue_margin_scatter(product_df), use_container_width=True, config={"displayModeBar": False})

    section_title("Where Revenue and Profit Diverge")
    median_rev = product_df["net_revenue"].median()
    dilutive = product_df[(product_df["net_revenue"] >= median_rev) & (product_df["contribution_margin_pct"] < 0.15)].sort_values("net_revenue", ascending=False)
    bundles = product_df[product_df["category"] == "Bundles & Sets"]

    if not dilutive.empty:
        rows = "".join(
            f'<div class="pp-insight bad">'
            f'<b>{r.product_name}</b> generated {metrics.fmt_currency(r.net_revenue)} in net revenue but only a '
            f'{metrics.fmt_pct(r.contribution_margin_pct)} contribution margin — it is a top-line contributor and a margin drag at the same time.'
            f"</div>"
            for r in dilutive.itertuples()
        )
        st.markdown(rows, unsafe_allow_html=True)
    else:
        st.markdown('<div class="pp-insight good">No above-median-revenue products are currently running below a 15% contribution margin.</div>', unsafe_allow_html=True)

    if not bundles.empty:
        avg_bundle_margin = bundles["contribution_margin_pct"].mean()
        avg_other_margin = product_df[product_df["category"] != "Bundles & Sets"]["contribution_margin_pct"].mean()
        bundle_aov = bundles["aov"].mean()
        other_aov = product_df[product_df["category"] != "Bundles & Sets"]["aov"].mean()
        st.markdown(
            f'<div class="pp-insight warn"><b>Bundle effect:</b> Bundles & Sets carry a '
            f'{metrics.fmt_currency(bundle_aov)} average order value vs. {metrics.fmt_currency(other_aov)} for single-item products, '
            f'but average contribution margin is {metrics.fmt_pct(avg_bundle_margin)} vs. {metrics.fmt_pct(avg_other_margin)} elsewhere — '
            f'bundles lift AOV and unit economics look fine on the surface, but heavier discounting and higher COGS compress the margin per dollar of revenue.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("Methodology"):
        st.markdown(
            "Product-level contribution profit excludes shipping cost and payment processing fees "
            "(tracked at the order level, not per line item) — it nets out COGS and refunds only. "
            "See README for the full allocation methodology and its limitations."
        )


# ===========================================================================
# PAGE: Customer & Retention
# ===========================================================================
def page_customer_retention() -> None:
    st.title("Customer & Retention")
    st.caption("Repeat behavior, cohort retention, and acquisition channel quality beyond CAC.")

    if orders_f.empty:
        empty_state()
        return

    cust_summary = metrics.customer_summary(orders_f)

    cols = st.columns(4)
    cols[0].markdown(metric_card("Repeat Purchase Rate", metrics.fmt_pct(cust_summary["repeat_rate"])), unsafe_allow_html=True)
    cols[1].markdown(metric_card("New Customer AOV", metrics.fmt_currency(cust_summary["new_aov"])), unsafe_allow_html=True)
    cols[2].markdown(metric_card("Returning Customer AOV", metrics.fmt_currency(cust_summary["returning_aov"])), unsafe_allow_html=True)
    cols[3].markdown(metric_card("Unique Customers", metrics.fmt_number(cust_summary["customers"])), unsafe_allow_html=True)

    section_title("New vs. Returning Revenue Trend")
    nvr = metrics.new_vs_returning_trend(orders_f)
    st.plotly_chart(charts.new_vs_returning_bar(nvr), use_container_width=True, config={"displayModeBar": False})

    section_title("Cohort Retention", "% of each monthly acquisition cohort placing an order N months later — based on full 12-month order history, independent of the date filter above.")
    cohort_base = orders_all.copy()
    if f.channels:
        cohort_customers = cohort_base[cohort_base["is_new_customer"] & cohort_base["channel"].isin(f.channels)]["customer_id"].unique()
        cohort_base = cohort_base[cohort_base["customer_id"].isin(cohort_customers)]
    pivot = metrics.cohort_retention(cohort_base)
    if pivot.shape[1] > 1:
        st.plotly_chart(charts.retention_heatmap(pivot), use_container_width=True, config={"displayModeBar": False})
    else:
        empty_state("Not enough cohort history yet for the current filter selection.")

    left, right = st.columns(2)
    with left:
        section_title("Customer Lifetime Revenue Distribution", "Total net revenue per customer, full history")
        ltv = orders_all.copy()
        ltv["net_revenue"] = ltv["gross_item_revenue"] - ltv["discount_amount"] + ltv["shipping_revenue"] + ltv["tax_amount"]
        ltv_by_cust = ltv.groupby("customer_id")["net_revenue"].sum()
        import plotly.express as px
        from src.styles import COLOR_PURPLE
        fig = px.histogram(ltv_by_cust, nbins=40, color_discrete_sequence=[COLOR_PURPLE])
        fig.update_layout(showlegend=False, xaxis_title="Lifetime Net Revenue ($)", yaxis_title="Customers", height=340,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        section_title("Acquisition Channel Quality", "First-order contribution profit & repeat rate by channel")
        cq = metrics.channel_quality_table(orders_f)
        disp = cq.copy()
        disp["avg_first_order_contribution_profit"] = disp["avg_first_order_contribution_profit"].map(metrics.fmt_currency)
        disp["repeat_rate"] = disp["repeat_rate"].map(metrics.fmt_pct)
        disp = disp.rename(columns={"channel": "Channel", "new_customers": "New Customers",
                                     "avg_first_order_contribution_profit": "Avg. First-Order Profit", "repeat_rate": "Repeat Rate"})
        st.dataframe(disp, use_container_width=True, hide_index=True)

    st.markdown(
        f'<div class="pp-insight"><b>Why this matters:</b> {insights.customer_quality_commentary(metrics.channel_quality_table(orders_f))}</div>',
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE: Attribution & Tracking Health
# ===========================================================================
def page_attribution_tracking() -> None:
    st.title("Attribution & Tracking Health")
    st.caption("Where order data, GA4-style session tracking, and ad-platform reporting agree — and where they don't.")

    if orders_f.empty:
        empty_state()
        return

    section_title("Revenue Reconciliation", "Same paid-channel scope (Google Ads + Meta Ads), three numbers — the gap itself is the signal")
    recon = metrics.revenue_reconciliation(orders_f, sessions_f, ad_spend_f)
    st.plotly_chart(charts.revenue_reconciliation_bar(recon), use_container_width=True, config={"displayModeBar": False})
    gap_pct = metrics.safe_div(
        recon["ad_platform_attributed_revenue"] - recon["order_system_revenue"], recon["order_system_revenue"]
    )
    direction = "more" if gap_pct >= 0 else "less"
    st.caption(
        f"For orders placed through Google Ads and Meta Ads specifically, ad platforms report "
        f"{metrics.fmt_pct(abs(gap_pct))} {direction} revenue than the order system attributes to those same channels — "
        f"typical of generous attribution windows and view-through credit. GA4-style tracked revenue "
        f"({metrics.fmt_currency(recon['ga4_tracked_revenue'])}) sits between the two, short of the order-system figure "
        f"due to the tracking gaps quantified below."
    )

    section_title("Attribution Model Comparison", "Channel revenue reallocates depending on how credit is assigned across the path")
    model = st.selectbox("Attribution model", metrics.ATTRIBUTION_MODELS, index=0)
    attr_df = metrics.attributed_revenue_by_channel(sessions_f, orders_f, model)
    st.plotly_chart(charts.attribution_channel_bar(attr_df), use_container_width=True, config={"displayModeBar": False})

    with st.expander("How each model assigns credit"):
        st.markdown(
            """
- **Last Click** — 100% of order revenue credited to the final touchpoint before purchase (closest to default GA4/Shopify behavior).
- **First Click** — 100% credited to the touchpoint that started the journey (best reflects top-of-funnel discovery).
- **Linear** — Credit split evenly across every touchpoint in the path.
- **Data-Informed (proxy)** — A U-shaped heuristic (40% first touch / 40% last touch / 20% split across the middle), standing in for a full data-driven model, which requires a trained conversion-probability model.
            """
        )

    section_title("Conversion Funnel", "Sessions → Product Views → Add to Cart → Checkout → Purchase")
    funnel_df = metrics.funnel_metrics(sessions_f)
    fc1, fc2 = st.columns([1.4, 1])
    with fc1:
        st.plotly_chart(charts.funnel_chart(funnel_df), use_container_width=True, config={"displayModeBar": False})
    with fc2:
        disp = funnel_df.copy()
        disp["conversion_from_prev"] = disp["conversion_from_prev"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
        disp["conversion_from_first"] = disp["conversion_from_first"].map(lambda v: metrics.fmt_pct(v) if pd.notna(v) else "—")
        disp = disp.rename(columns={"stage": "Stage", "count": "Count", "conversion_from_prev": "Step Conv.", "conversion_from_first": "Of Total"})
        st.dataframe(disp, use_container_width=True, hide_index=True)

    section_title("Tracking Health")
    th = metrics.tracking_health(orders_f, sessions_f)
    g1, g2 = st.columns([1, 1.6])
    with g1:
        st.plotly_chart(charts.tracking_health_gauge(th["score"]), use_container_width=True, config={"displayModeBar": False})
    with g2:
        st.plotly_chart(charts.tracking_issues_bar(th["issues"]), use_container_width=True, config={"displayModeBar": False})

    section_title("Recommended Fixes", "Realistic GTM/GA4 implementation steps to close the gaps above")
    fixes = [
        ("Standardize UTM governance", "Enforce a UTM naming convention (source/medium/campaign/content) across Google Ads, Meta Ads, and email/SMS via a shared naming template and campaign-builder validation before launch."),
        ("Deduplicate purchase events using transaction_id", "Configure the GA4 purchase event (and any server-side pixel) to dedupe on a stable transaction_id, and add a BigQuery/warehouse-side dedupe step as a backstop against double-fires."),
        ("Validate GA4 purchase revenue against Shopify/order data", "Run a daily reconciliation job comparing GA4 purchase revenue to Shopify order revenue by transaction_id; alert when the delta exceeds a defined threshold."),
        ("Persist campaign parameters across checkout", "Store UTM/click-id parameters in a first-party cookie or backend session at landing, and re-attach them through checkout/redirects so paid traffic isn't reclassified as direct after a domain hop."),
        ("Monitor consent-mode-related tracking gaps", "Segment tracking coverage by consent status to separate genuine unattributed revenue from consent-mode modeling gaps, and monitor the trend after any CMP or consent-banner change."),
    ]
    for title, detail in fixes:
        st.markdown(f'<div class="pp-reco"><b>{title}.</b> {detail}</div>', unsafe_allow_html=True)


# ===========================================================================
# PAGE: Data Explorer
# ===========================================================================
def page_data_explorer() -> None:
    st.title("Data Explorer")
    st.caption("Browse raw source tables, or query them directly with DuckDB.")

    tables = {
        "orders": orders_all, "customers": customers_all, "products": products_all,
        "refunds": refunds_all, "ad_spend": ad_spend_all, "web_sessions": sessions_all,
    }

    tab1, tab2 = st.tabs(["Table Browser", "SQL Query (DuckDB)"])

    with tab1:
        table_name = st.selectbox("Dataset", list(tables.keys()))
        df = tables[table_name]
        search = st.text_input("Search (matches any column, case-insensitive)", "")
        view = df
        if search:
            mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            view = df[mask]
        st.caption(f"{len(view):,} of {len(df):,} rows")
        st.dataframe(view.head(2000), use_container_width=True, height=460)
        st.download_button(
            "Download filtered CSV", view.to_csv(index=False).encode("utf-8"),
            file_name=f"{table_name}_filtered.csv", mime="text/csv",
        )

    with tab2:
        st.caption("Read-only SELECT queries against the six source tables, run locally with DuckDB.")
        examples = {
            "Net revenue by channel": (
                "select channel,\n"
                "       round(sum(gross_item_revenue - discount_amount + shipping_revenue + tax_amount), 2) as net_revenue,\n"
                "       count(*) as orders\n"
                "from orders\n"
                "group by channel\n"
                "order by net_revenue desc"
            ),
            "Top 10 customers by lifetime revenue": (
                "select customer_id,\n"
                "       round(sum(gross_item_revenue - discount_amount + shipping_revenue + tax_amount), 2) as lifetime_revenue,\n"
                "       count(*) as orders\n"
                "from orders\n"
                "group by customer_id\n"
                "order by lifetime_revenue desc\n"
                "limit 10"
            ),
            "Monthly ad spend and platform-reported revenue": (
                "select date_trunc('month', date) as month, channel,\n"
                "       round(sum(spend), 2) as spend,\n"
                "       round(sum(platform_reported_revenue), 2) as platform_revenue\n"
                "from ad_spend\n"
                "group by 1, 2\n"
                "order by 1, 2"
            ),
            "Refund rate by product": (
                "select p.product_name,\n"
                "       count(distinct r.order_id) as refunded_orders,\n"
                "       count(distinct o.order_id) as total_orders,\n"
                "       round(count(distinct r.order_id) * 100.0 / count(distinct o.order_id), 1) as refund_rate_pct\n"
                "from orders o\n"
                "join products p on p.product_id = o.product_id\n"
                "left join refunds r on r.order_id = o.order_id\n"
                "group by p.product_name\n"
                "order by refund_rate_pct desc"
            ),
        }
        choice = st.selectbox("Example queries", ["(custom)"] + list(examples.keys()))
        default_sql = examples.get(choice, "select * from orders limit 20")
        sql = st.text_area("SQL", value=default_sql, height=160)
        run = st.button("Run query", type="primary")
        if run:
            cleaned = sql.strip().lower()
            if not cleaned.startswith("select") and not cleaned.startswith("with"):
                st.error("Only read-only SELECT / WITH queries are supported here.")
            else:
                try:
                    con = duckdb.connect(database=":memory:")
                    con.register("orders", orders_all)
                    con.register("customers", customers_all)
                    con.register("products", products_all)
                    con.register("refunds", refunds_all)
                    con.register("ad_spend", ad_spend_all)
                    con.register("web_sessions", sessions_all)
                    result = con.execute(sql).df()
                    st.success(f"{len(result):,} rows returned")
                    st.dataframe(result, use_container_width=True, height=420)
                    st.download_button(
                        "Download result CSV", result.to_csv(index=False).encode("utf-8"),
                        file_name="query_result.csv", mime="text/csv",
                    )
                except Exception as e:
                    st.error(f"Query error: {e}")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
PAGES = {
    "Executive Overview": page_executive_overview,
    "Paid Media Performance": page_paid_media,
    "Product & Profitability": page_product_profitability,
    "Customer & Retention": page_customer_retention,
    "Attribution & Tracking Health": page_attribution_tracking,
    "Data Explorer": page_data_explorer,
}

PAGES[page]()
