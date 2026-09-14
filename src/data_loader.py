"""
Data loading, typing, and joining for Keel.

All CSVs live in data/. Everything is loaded once and cached via
st.cache_data; downstream pages filter the cached frames rather than
re-reading disk.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@dataclass
class Filters:
    start_date: date
    end_date: date
    channels: list[str] = field(default_factory=list)
    customer_type: str = "All"  # "All" | "New" | "Returning"
    device: list[str] = field(default_factory=list)
    campaign: list[str] = field(default_factory=list)


@st.cache_data(show_spinner=False)
def load_raw() -> dict[str, pd.DataFrame]:
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"), dtype={"customer_id": str})
    orders = pd.read_csv(
        os.path.join(DATA_DIR, "orders.csv"),
        dtype={"order_id": str, "transaction_id": str, "customer_id": str, "product_id": str},
        parse_dates=["order_date"],
    )
    refunds = pd.read_csv(os.path.join(DATA_DIR, "refunds.csv"), dtype={"order_id": str}, parse_dates=["refund_date"])
    ad_spend = pd.read_csv(os.path.join(DATA_DIR, "ad_spend.csv"), parse_dates=["date"])
    web_sessions = pd.read_csv(
        os.path.join(DATA_DIR, "web_sessions.csv"),
        dtype={"customer_id": str, "transaction_id": str, "journey_id": str},
        parse_dates=["session_date"],
    )

    customers["first_order_date"] = pd.to_datetime(customers["first_order_date"])

    return {
        "products": products,
        "customers": customers,
        "orders": orders,
        "refunds": refunds,
        "ad_spend": ad_spend,
        "web_sessions": web_sessions,
    }


@st.cache_data(show_spinner=False)
def build_orders_enriched() -> pd.DataFrame:
    """Orders joined with product info and per-order refund totals."""
    raw = load_raw()
    orders = raw["orders"].copy()
    products = raw["products"][["product_id", "product_name", "category", "unit_cogs"]]
    refunds = raw["refunds"]

    refund_by_order = refunds.groupby("order_id")["refund_amount"].sum().rename("refund_amount")
    orders = orders.merge(products, on="product_id", how="left")
    orders = orders.merge(refund_by_order, on="order_id", how="left")
    orders["refund_amount"] = orders["refund_amount"].fillna(0.0)
    orders["is_refunded"] = orders["refund_amount"] > 0

    orders["net_item_revenue"] = orders["gross_item_revenue"] - orders["discount_amount"]
    orders["net_revenue"] = (
        orders["gross_item_revenue"] - orders["discount_amount"] + orders["shipping_revenue"] + orders["tax_amount"]
    )
    orders["contribution_profit"] = (
        orders["net_revenue"] - orders["cogs"] - orders["shipping_cost"] - orders["payment_fee"] - orders["refund_amount"]
    )
    return orders


@st.cache_data(show_spinner=False)
def date_bounds() -> tuple[date, date]:
    orders = load_raw()["orders"]
    return orders["order_date"].min().date(), orders["order_date"].max().date()


def filter_orders(orders: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = (orders["order_date"].dt.date >= f.start_date) & (orders["order_date"].dt.date <= f.end_date)
    if f.channels:
        mask &= orders["channel"].isin(f.channels)
    if f.customer_type == "New":
        mask &= orders["is_new_customer"]
    elif f.customer_type == "Returning":
        mask &= ~orders["is_new_customer"]
    if f.device:
        mask &= orders["device"].isin(f.device)
    if f.campaign:
        mask &= orders["campaign"].isin(f.campaign)
    return orders.loc[mask]


def filter_ad_spend(ad_spend: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = (ad_spend["date"].dt.date >= f.start_date) & (ad_spend["date"].dt.date <= f.end_date)
    if f.channels:
        mask &= ad_spend["channel"].isin(f.channels)
    if f.campaign:
        mask &= ad_spend["campaign"].isin(f.campaign)
    return ad_spend.loc[mask]


def filter_sessions(sessions: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = (sessions["session_date"].dt.date >= f.start_date) & (sessions["session_date"].dt.date <= f.end_date)
    if f.channels:
        mask &= sessions["source"].isin(f.channels)
    if f.device:
        mask &= sessions["device"].isin(f.device)
    return sessions.loc[mask]


def comparison_window(f: Filters) -> Filters:
    """Prior period of equal length immediately preceding the selected range."""
    span = (f.end_date - f.start_date).days + 1
    prior_end = f.start_date - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=span - 1)
    return Filters(
        start_date=prior_start.date() if hasattr(prior_start, "date") else prior_start,
        end_date=prior_end.date() if hasattr(prior_end, "date") else prior_end,
        channels=f.channels,
        customer_type=f.customer_type,
        device=f.device,
        campaign=f.campaign,
    )
