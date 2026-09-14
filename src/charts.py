"""Plotly chart builders for Keel. Every chart shares a common dark
template, currency-aware hover formatting, and the app's color vocabulary."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.styles import (
    CATEGORY_COLORS, CHANNEL_COLORS, COLOR_AMBER, COLOR_BG_ELEVATED, COLOR_BLUE,
    COLOR_BORDER, COLOR_CARD, COLOR_GREEN, COLOR_PURPLE, COLOR_RED, COLOR_SUBTEXT,
    COLOR_TEXT, FONT_FAMILY, PLOTLY_SEQUENCE,
)

BASE_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, color=COLOR_SUBTEXT, size=13),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12, color=COLOR_TEXT)),
    hoverlabel=dict(bgcolor=COLOR_CARD, font_size=12, font_family=FONT_FAMILY, font_color=COLOR_TEXT, bordercolor=COLOR_BORDER),
)

GRID_STYLE = dict(gridcolor=COLOR_BORDER, zeroline=False, showline=False, color=COLOR_SUBTEXT)


def _apply_base(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(**BASE_LAYOUT, height=height)
    fig.update_xaxes(**GRID_STYLE)
    fig.update_yaxes(**GRID_STYLE)
    return fig


def revenue_spend_profit_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["day"], y=df["net_revenue"], name="Net Revenue", mode="lines",
        line=dict(color=COLOR_BLUE, width=2.4), fill="tozeroy", fillcolor="rgba(91,141,255,0.10)",
        hovertemplate="%{x|%b %d, %Y}<br>Net Revenue: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["day"], y=df["ad_spend"], name="Ad Spend", mode="lines",
        line=dict(color=COLOR_RED, width=1.8, dash="dot"),
        hovertemplate="%{x|%b %d, %Y}<br>Ad Spend: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["day"], y=df["contribution_profit"], name="Contribution Profit", mode="lines",
        line=dict(color=COLOR_GREEN, width=2.4),
        hovertemplate="%{x|%b %d, %Y}<br>Contribution Profit: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return _apply_base(fig, height=380)


def revenue_mix_donut(channel_df: pd.DataFrame) -> go.Figure:
    colors = [CHANNEL_COLORS.get(c, COLOR_SUBTEXT) for c in channel_df["channel"]]
    fig = go.Figure(go.Pie(
        labels=channel_df["channel"], values=channel_df["net_revenue"], hole=0.58,
        marker=dict(colors=colors, line=dict(color=COLOR_BG_ELEVATED, width=2)),
        textinfo="percent", textfont=dict(size=12, color="#060709"),
        hovertemplate="%{label}<br>Net Revenue: $%{value:,.0f} (%{percent})<extra></extra>",
    ))
    fig.update_layout(showlegend=True)
    return _apply_base(fig, height=340)


def new_vs_returning_bar(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="month", y="net_revenue", color="segment", barmode="stack",
        color_discrete_map={"New": COLOR_PURPLE, "Returning": COLOR_GREEN},
        labels={"month": "", "net_revenue": "Net Revenue"},
    )
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>")
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    fig.update_layout(legend_title_text="")
    return _apply_base(fig, height=340)


def roas_margin_scatter(df: pd.DataFrame, label_col: str = "campaign") -> go.Figure:
    df = df.copy()
    df["contribution_margin_pct_display"] = df["contribution_margin_pct"] * 100
    fig = px.scatter(
        df, x="roas", y="contribution_margin_pct_display", size="ad_spend", color="channel",
        color_discrete_map=CHANNEL_COLORS, hover_name=label_col, size_max=48,
        labels={"roas": "ROAS (Net Revenue / Spend)", "contribution_margin_pct_display": "Contribution Margin %"},
    )
    fig.add_hline(y=0, line_dash="dot", line_color=COLOR_SUBTEXT, opacity=0.6)
    fig.add_vline(x=3, line_dash="dot", line_color=COLOR_SUBTEXT, opacity=0.4,
                   annotation_text="ROAS = 3x reference", annotation_font_size=10)
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>ROAS: %{x:.2f}x<br>Contribution Margin: %{y:.1f}%<br>Spend: $%{marker.size:,.0f}<extra></extra>")
    fig.update_yaxes(ticksuffix="%")
    return _apply_base(fig, height=420)


def spend_roas_cac_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["day"], y=df["ad_spend"], name="Ad Spend", marker_color="rgba(139,143,163,0.22)",
                          hovertemplate="%{x|%b %d}<br>Spend: $%{y:,.0f}<extra></extra>", yaxis="y"))
    fig.add_trace(go.Scatter(x=df["day"], y=df["roas"], name="ROAS", mode="lines", line=dict(color=COLOR_BLUE, width=2.2),
                              hovertemplate="%{x|%b %d}<br>ROAS: %{y:.2f}x<extra></extra>", yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="Ad Spend ($)", tickprefix="$", **GRID_STYLE),
        yaxis2=dict(title="ROAS", overlaying="y", side="right", showgrid=False),
    )
    return _apply_base(fig, height=340)


def product_margin_rank(df: pd.DataFrame, n: int = 15) -> go.Figure:
    d = df.sort_values("contribution_margin_pct", ascending=True).tail(n)
    colors = [COLOR_GREEN if v >= 0.2 else (COLOR_AMBER if v >= 0 else COLOR_RED) for v in d["contribution_margin_pct"]]
    fig = go.Figure(go.Bar(
        x=d["contribution_margin_pct"] * 100, y=d["product_name"], orientation="h",
        marker_color=colors,
        hovertemplate="%{y}<br>Contribution Margin: %{x:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(ticksuffix="%", title="Contribution Margin %")
    return _apply_base(fig, height=max(340, 26 * len(d)))


def product_revenue_margin_scatter(df: pd.DataFrame) -> go.Figure:
    d = df.copy()
    d["contribution_margin_pct_display"] = d["contribution_margin_pct"] * 100
    colors = [CATEGORY_COLORS.get(c, COLOR_SUBTEXT) for c in d["category"]]
    fig = go.Figure(go.Scatter(
        x=d["net_revenue"], y=d["contribution_margin_pct_display"], mode="markers+text",
        text=d["product_name"], textposition="top center", textfont=dict(size=10, color=COLOR_SUBTEXT),
        marker=dict(size=d["units_sold"].clip(lower=1) ** 0.5 * 2.4 + 8, color=colors, line=dict(color=COLOR_BG_ELEVATED, width=1)),
        hovertemplate="<b>%{text}</b><br>Net Revenue: $%{x:,.0f}<br>Contribution Margin: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=COLOR_SUBTEXT, opacity=0.6)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f", title="Net Revenue")
    fig.update_yaxes(ticksuffix="%", title="Contribution Margin %")
    return _apply_base(fig, height=440)


def retention_heatmap(pivot: pd.DataFrame) -> go.Figure:
    z = (pivot * 100).round(1)
    text = z.map(lambda v: "" if pd.isna(v) else f"{v:g}%")
    fig = go.Figure(go.Heatmap(
        z=z.values, x=[f"Month {c}" for c in z.columns], y=z.index,
        colorscale=[[0, "#2A1420"], [0.5, "#2A2414"], [1, "#123324"]],
        text=text.values, texttemplate="%{text}", textfont=dict(size=10, color=COLOR_TEXT),
        hovertemplate="Cohort: %{y}<br>%{x}<br>Retention: %{z}%<extra></extra>",
        colorbar=dict(title="Retention %", ticksuffix="%", outlinewidth=0, tickfont=dict(color=COLOR_SUBTEXT)),
        xgap=3, ygap=3,
    ))
    fig.update_layout(xaxis_title="Months Since First Order", yaxis_title="Acquisition Cohort")
    fig.update_yaxes(type="category", dtick=1)
    return _apply_base(fig, height=max(320, 34 * len(z)))


def funnel_chart(funnel_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=funnel_df["stage"], x=funnel_df["count"],
        textinfo="value+percent initial",
        textfont=dict(color="#06070A", size=12),
        marker=dict(color=PLOTLY_SEQUENCE[: len(funnel_df)]),
        connector=dict(line=dict(color=COLOR_BORDER, width=1)),
    ))
    return _apply_base(fig, height=380)


def attribution_channel_bar(df: pd.DataFrame) -> go.Figure:
    d = df.sort_values("revenue", ascending=True)
    colors = [CHANNEL_COLORS.get(c, COLOR_SUBTEXT) for c in d["channel"]]
    fig = go.Figure(go.Bar(
        x=d["revenue"], y=d["channel"], orientation="h", marker_color=colors,
        hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<extra></extra>",
    ))
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    return _apply_base(fig, height=340)


def tracking_health_gauge(score: float) -> go.Figure:
    color = COLOR_GREEN if score >= 80 else (COLOR_AMBER if score >= 60 else COLOR_RED)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100", "font": {"size": 34, "color": COLOR_TEXT}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": COLOR_SUBTEXT, "tickfont": {"color": COLOR_SUBTEXT}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": COLOR_CARD,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 60], "color": "#2A1620"},
                {"range": [60, 80], "color": "#2A2216"},
                {"range": [80, 100], "color": "#16261F"},
            ],
        },
    ))
    return _apply_base(fig, height=260)


def tracking_issues_bar(issues: dict) -> go.Figure:
    df = pd.DataFrame({"issue": list(issues.keys()), "rate": list(issues.values())}).sort_values("rate")
    colors = [COLOR_AMBER if v < 0.15 else COLOR_RED for v in df["rate"]]
    fig = go.Figure(go.Bar(
        x=df["rate"] * 100, y=df["issue"], orientation="h", marker_color=colors,
        hovertemplate="%{y}<br>%{x:.1f}% of records<extra></extra>",
    ))
    fig.update_xaxes(ticksuffix="%", title="Share of records affected")
    return _apply_base(fig, height=280)


def revenue_reconciliation_bar(recon: dict) -> go.Figure:
    labels = ["Order System\n(Paid Channels)", "GA4-Style Tracked\n(Paid Channels)", "Ad Platform\nAttributed Revenue"]
    values = [recon["order_system_revenue"], recon["ga4_tracked_revenue"], recon["ad_platform_attributed_revenue"]]
    colors = [COLOR_BLUE, COLOR_PURPLE, COLOR_AMBER]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors, text=[f"${v:,.0f}" for v in values], textposition="outside",
        textfont=dict(color=COLOR_TEXT),
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return _apply_base(fig, height=360)


def cac_by_channel_bar(df: pd.DataFrame) -> go.Figure:
    d = df[df["ad_spend"] > 0].sort_values("cac")
    colors = [CHANNEL_COLORS.get(c, COLOR_SUBTEXT) for c in d["channel"]]
    fig = go.Figure(go.Bar(
        x=d["channel"], y=d["cac"], marker_color=colors,
        hovertemplate="%{x}<br>CAC: $%{y:,.2f}<extra></extra>",
    ))
    fig.update_yaxes(tickprefix="$", title="CAC")
    return _apply_base(fig, height=320)
