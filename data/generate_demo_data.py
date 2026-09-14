"""
Seed data generator for Luma Skin's order, session, and ad-spend history.

Produces a full deterministic (seeded) 12-month dataset -- run it once to
populate data/ before starting the app.

Run:
    python data/generate_demo_data.py

Produces (in this directory):
    products.csv
    customers.csv
    orders.csv
    refunds.csv
    ad_spend.csv
    web_sessions.csv

Design notes (why the data looks the way it does)
---------------------------------------------------
The generator builds in the kind of messiness a real growth team deals
with, so the app has something honest to analyze:

  * Bundles/sets have healthy revenue but thin contribution margin (high
    COGS ratio + heavier discounting) -- a "revenue vs. profit" story.
  * Meta Ads prospecting campaigns post attractive platform-reported ROAS
    but the platform inflates results vs. actual attributed order revenue
    (view-through / attribution-window generosity) -- a "ROAS != profit"
    story.
  * ~10-12% of orders have no matching GA4-style session (tracking gaps),
    a slice of paid sessions are missing UTM parameters, ~2% of purchase
    sessions are double-fired (duplicate transaction_id), and matched
    sessions sometimes report a slightly different revenue figure than the
    order system -- an "attribution & tracking health" story.
  * Seasonality includes a Black Friday / Cyber Monday spike, a holiday
    shipping season lift, and a January lull.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Global config
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

TODAY = dt.date.today()
END_DATE = TODAY - dt.timedelta(days=1)
START_DATE = END_DATE - dt.timedelta(days=364)
ALL_DATES = pd.date_range(START_DATE, END_DATE, freq="D")

OUT_DIR = __file__.rsplit("/", 1)[0]


def _id(prefix: str, n: int, width: int = 6) -> str:
    return f"{prefix}{n:0{width}d}"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
PRODUCTS = [
    # product_id, name, category, price, cogs, launch_offset_days
    ("SKU001", "Gentle Hydra Cleanser", "Cleansers", 24.00, 7.20, 0),
    ("SKU002", "Clarify Foaming Cleanser", "Cleansers", 22.00, 6.60, 0),
    ("SKU003", "Vitamin C Brightening Serum", "Serums", 48.00, 12.00, 0),
    ("SKU004", "Retinol Renewal Serum", "Serums", 56.00, 15.68, 30),
    ("SKU005", "Hyaluronic Moisture Serum", "Serums", 42.00, 10.50, 0),
    ("SKU006", "Daily Barrier Moisturizer", "Moisturizers", 38.00, 11.40, 0),
    ("SKU007", "Overnight Repair Cream", "Moisturizers", 52.00, 16.64, 60),
    ("SKU008", "Mineral Sunscreen SPF 40", "Sunscreen", 32.00, 9.60, 0),
    ("SKU009", "Bright Eyes Depuffing Cream", "Eye Care", 34.00, 10.88, 90),
    ("SKU010", "Clay Detox Mask", "Masks", 28.00, 8.40, 0),
    ("SKU011", "The Essentials Bundle", "Bundles & Sets", 98.00, 38.00, 45),
    ("SKU012", "Glow Ritual Bundle (5-Piece)", "Bundles & Sets", 145.00, 61.00, 120),
]

products_df = pd.DataFrame(
    PRODUCTS,
    columns=["product_id", "product_name", "category", "unit_price", "unit_cogs", "launch_offset_days"],
)
products_df["launch_date"] = products_df["launch_offset_days"].apply(
    lambda d: (START_DATE + dt.timedelta(days=int(d))).isoformat()
)
products_df = products_df.drop(columns=["launch_offset_days"])
products_df["margin_pct_at_list_price"] = (
    (products_df["unit_price"] - products_df["unit_cogs"]) / products_df["unit_price"]
).round(4)

# Popularity weights -- bundles and hero serums sell more, niche items less.
PRODUCT_WEIGHTS = {
    "SKU001": 0.13, "SKU002": 0.08, "SKU003": 0.14, "SKU004": 0.09,
    "SKU005": 0.11, "SKU006": 0.10, "SKU007": 0.06, "SKU008": 0.09,
    "SKU009": 0.05, "SKU010": 0.06, "SKU011": 0.06, "SKU012": 0.03,
}
PRODUCT_IDS = list(PRODUCT_WEIGHTS.keys())
PRODUCT_W = np.array([PRODUCT_WEIGHTS[p] for p in PRODUCT_IDS])
PRODUCT_W = PRODUCT_W / PRODUCT_W.sum()
PRODUCT_LOOKUP = products_df.set_index("product_id")[["unit_price", "unit_cogs", "category"]].to_dict("index")

# ---------------------------------------------------------------------------
# Channel / campaign taxonomy
# ---------------------------------------------------------------------------
CHANNELS = ["Google Ads", "Meta Ads", "Organic Search", "Email/SMS", "Direct", "Organic Social", "Unattributed"]

CAMPAIGNS = {
    "Google Ads": [
        ("Search - Brand", "N/A"),
        ("Search - Nonbrand Skincare", "N/A"),
        ("Shopping - Bestsellers", "N/A"),
        ("PMax - Skincare Prospecting", "N/A"),
    ],
    "Meta Ads": [
        ("Prospecting - Broad", "Advantage+ Broad"),
        ("Prospecting - Lookalike 1%", "LAL 1% Purchasers"),
        ("Retargeting - Cart Abandon", "Retarget - Added to Cart 7d"),
        ("Retargeting - Engaged 30d", "Retarget - Engaged 30d"),
    ],
    "Organic Search": [("(organic)", "N/A")],
    "Email/SMS": [
        ("Flow - Welcome Series", "N/A"),
        ("Flow - Abandoned Cart", "N/A"),
        ("Campaign - Monthly Newsletter", "N/A"),
        ("Flow - Post Purchase Winback", "N/A"),
    ],
    "Direct": [("(direct)", "N/A")],
    "Organic Social": [("(organic social)", "N/A")],
    "Unattributed": [("(not set)", "N/A")],
}

PAID_CHANNELS = ["Google Ads", "Meta Ads"]

# Target blended ROAS per (channel, campaign) -- drives ad_spend backed out
# from attributed order revenue, with independent noise per day.
TARGET_ROAS = {
    ("Google Ads", "Search - Brand"): 9.5,
    ("Google Ads", "Search - Nonbrand Skincare"): 3.1,
    ("Google Ads", "Shopping - Bestsellers"): 3.6,
    ("Google Ads", "PMax - Skincare Prospecting"): 2.5,
    ("Meta Ads", "Prospecting - Broad"): 1.7,
    ("Meta Ads", "Prospecting - Lookalike 1%"): 2.3,
    ("Meta Ads", "Retargeting - Cart Abandon"): 5.6,
    ("Meta Ads", "Retargeting - Engaged 30d"): 3.0,
}

# How much the ad platform over-reports revenue vs. actual attributed order
# revenue (view-through / generous attribution windows).
PLATFORM_INFLATION = {
    "Google Ads": (1.03, 1.22),
    "Meta Ads": (1.18, 1.55),
}

# New-customer acquisition channel mix (baseline, before BFCM promo skew)
NEW_CHANNEL_WEIGHTS = {
    "Meta Ads": 0.30, "Google Ads": 0.27, "Organic Search": 0.18,
    "Organic Social": 0.08, "Direct": 0.10, "Email/SMS": 0.03, "Unattributed": 0.04,
}
# Returning-customer order channel mix (loyalty / retargeting dominated)
RET_CHANNEL_WEIGHTS = {
    "Email/SMS": 0.38, "Direct": 0.22, "Organic Search": 0.14,
    "Meta Ads": 0.12, "Google Ads": 0.08, "Organic Social": 0.04, "Unattributed": 0.02,
}


def _weighted_channel(weights: dict) -> str:
    chans = list(weights.keys())
    w = np.array(list(weights.values()))
    return rng.choice(chans, p=w / w.sum())


def _campaign_for(channel: str) -> tuple[str, str]:
    opts = CAMPAIGNS[channel]
    idx = rng.integers(0, len(opts))
    return opts[idx]


# ---------------------------------------------------------------------------
# Seasonality
# ---------------------------------------------------------------------------
def seasonality_multiplier(d: dt.date) -> float:
    month, day = d.month, d.day
    mult = 1.0
    # Black Friday / Cyber Monday window
    if (month == 11 and day >= 24) or (month == 12 and day <= 2):
        mult *= 2.6
    # December holiday shipping season
    elif month == 12 and 3 <= day <= 22:
        mult *= 1.45
    # Post-holiday lull
    elif month == 12 and day >= 23:
        mult *= 0.65
    elif month == 1 and day <= 7:
        mult *= 0.7
    elif month == 1:
        mult *= 0.88
    # Summer dip
    elif month in (6, 7, 8):
        mult *= 0.87
    # Slight spring lift (new routines)
    elif month in (3, 4):
        mult *= 1.08

    # Weekly pattern: weekends stronger, Monday softest
    dow = d.weekday()  # 0=Mon
    weekday_factor = {0: 0.90, 1: 0.97, 2: 1.0, 3: 1.02, 4: 1.08, 5: 1.15, 6: 1.10}[dow]
    mult *= weekday_factor

    # Gentle growth trend across the 12 months (brand growing)
    days_elapsed = (d - START_DATE).days
    growth = 1.0 + (days_elapsed / 365.0) * 0.35
    mult *= growth
    return mult


DAILY_BASE_ORDERS = 34  # baseline orders/day before seasonality/growth
daily_targets = {d.date(): max(6, int(round(DAILY_BASE_ORDERS * seasonality_multiplier(d.date())))) for d in ALL_DATES}
TOTAL_ORDERS_TARGET = sum(daily_targets.values())

# ---------------------------------------------------------------------------
# Devices / regions
# ---------------------------------------------------------------------------
DEVICES = ["Mobile", "Desktop", "Tablet"]
DEVICE_W = [0.62, 0.33, 0.05]
REGIONS = ["West", "South", "Midwest", "Northeast"]
REGION_W = [0.30, 0.28, 0.22, 0.20]

LANDING_PAGES = [
    "/", "/products/vitamin-c-serum", "/products/glow-ritual-bundle",
    "/collections/bestsellers", "/products/retinol-renewal-serum",
    "/collections/skincare-sets", "/pages/about", "/products/mineral-sunscreen-spf-40",
    "/collections/all", "/products/daily-barrier-moisturizer",
]

# ---------------------------------------------------------------------------
# Customer + order simulation (day-by-day)
# ---------------------------------------------------------------------------
customers = {}          # customer_id -> dict
customer_order_hist = {}  # customer_id -> list of order dates
orders_rows = []
refunds_rows = []
touch_plans = []         # per-order pre-purchase touch info, consumed later for web_sessions

next_customer_num = 1
next_order_num = 100000
next_refund_num = 500000

REFUND_BASE_RATE = 0.065
REFUND_RATE_BY_PRODUCT = {"SKU004": 0.11, "SKU011": 0.09, "SKU012": 0.10}

for d in ALL_DATES:
    day = d.date()
    n_orders = daily_targets[day]
    is_bfcm = (day.month == 11 and day.day >= 24) or (day.month == 12 and day.day <= 2)

    # Share of orders from new customers: baseline ~62%, growing base means
    # slightly more returning traffic later, BFCM skews new-customer heavy
    # (promo-driven trial).
    days_elapsed = (day - START_DATE).days
    base_new_share = 0.66 - (days_elapsed / 365.0) * 0.14
    new_share = min(0.85, base_new_share + 0.15) if is_bfcm else max(0.42, base_new_share)

    existing_ids = list(customers.keys())

    for _ in range(n_orders):
        is_new = (len(existing_ids) == 0) or (rng.random() < new_share)

        if is_new:
            cid = _id("CUST", next_customer_num)
            next_customer_num += 1
            channel_weights = dict(NEW_CHANNEL_WEIGHTS)
            if is_bfcm:  # promo pushes more paid-social/search trial
                channel_weights["Meta Ads"] += 0.06
                channel_weights["Google Ads"] += 0.04
                channel_weights["Email/SMS"] = max(0.01, channel_weights["Email/SMS"] - 0.03)
            channel = _weighted_channel(channel_weights)
            campaign, ad_set = _campaign_for(channel)
            device = rng.choice(DEVICES, p=DEVICE_W)
            region = rng.choice(REGIONS, p=REGION_W)
            customers[cid] = {
                "customer_id": cid,
                "first_order_date": day.isoformat(),
                "acquisition_channel": channel,
                "acquisition_campaign": campaign,
                "region": region,
                "device": device,
            }
            customer_order_hist[cid] = [day]
            existing_ids.append(cid)
        else:
            # Weight returning customers toward more recent purchasers
            # (recency-weighted sample over a capped pool for performance).
            pool = existing_ids[-4000:] if len(existing_ids) > 4000 else existing_ids
            cid = pool[rng.integers(0, len(pool))]
            channel = _weighted_channel(RET_CHANNEL_WEIGHTS)
            campaign, ad_set = _campaign_for(channel)
            device = customers[cid]["device"] if rng.random() < 0.8 else rng.choice(DEVICES, p=DEVICE_W)
            region = customers[cid]["region"]
            customer_order_hist[cid].append(day)

        # ---- product & quantity ----
        product_id = rng.choice(PRODUCT_IDS, p=PRODUCT_W)
        pinfo = PRODUCT_LOOKUP[product_id]
        qty_roll = rng.random()
        quantity = 1 if qty_roll < 0.68 else (2 if qty_roll < 0.90 else rng.integers(3, 5))

        unit_price = pinfo["unit_price"]
        unit_cogs = pinfo["unit_cogs"]
        item_revenue = unit_price * quantity

        # ---- discounts ----
        if is_bfcm:
            disc_prob, disc_range = 0.72, (0.18, 0.30)
        elif channel == "Email/SMS" and campaign == "Flow - Abandoned Cart":
            disc_prob, disc_range = 0.9, (0.08, 0.12)
        else:
            disc_prob, disc_range = 0.24, (0.08, 0.20)
        discount_rate = rng.uniform(*disc_range) if rng.random() < disc_prob else 0.0
        discount_amount = round(item_revenue * discount_rate, 2)

        charged_pre_ship = item_revenue - discount_amount

        # ---- shipping ----
        shipping_revenue = 0.0 if charged_pre_ship >= 75 else 6.95
        region_ship_bump = {"West": 0.0, "South": 0.4, "Midwest": 0.9, "Northeast": 1.3}[region]
        shipping_cost = round(7.10 + region_ship_bump + rng.uniform(-0.6, 1.4), 2)

        # ---- tax ----
        taxed = rng.random() < 0.45
        tax_rate = rng.uniform(0.055, 0.095) if taxed else 0.0
        tax_amount = round((charged_pre_ship + shipping_revenue) * tax_rate, 2)

        gross_revenue = round(item_revenue + shipping_revenue + tax_amount, 2)
        charged_amount = round(charged_pre_ship + shipping_revenue + tax_amount, 2)
        payment_fee = round(charged_amount * 0.029 + 0.30, 2)
        cogs = round(unit_cogs * quantity, 2)

        order_id = _id("ORD", next_order_num)
        next_order_num += 1

        orders_rows.append({
            "order_id": order_id,
            "transaction_id": order_id,
            "order_date": day.isoformat(),
            "customer_id": cid,
            "is_new_customer": is_new,
            "channel": channel,
            "campaign": campaign,
            "device": device,
            "region": region,
            "product_id": product_id,
            "quantity": int(quantity),
            "unit_price": unit_price,
            "gross_item_revenue": round(item_revenue, 2),
            "discount_amount": discount_amount,
            "shipping_revenue": shipping_revenue,
            "tax_amount": tax_amount,
            "gross_revenue": gross_revenue,
            "cogs": cogs,
            "shipping_cost": shipping_cost,
            "payment_fee": payment_fee,
        })

        # ---- refunds ----
        refund_p = REFUND_RATE_BY_PRODUCT.get(product_id, REFUND_BASE_RATE)
        if rng.random() < refund_p:
            refund_frac = rng.choice([1.0, 0.5], p=[0.75, 0.25])
            refund_amount = round(charged_amount * refund_frac, 2)
            refund_delay = int(rng.integers(3, 22))
            refund_date = day + dt.timedelta(days=refund_delay)
            refunds_rows.append({
                "refund_id": _id("REF", next_refund_num),
                "order_id": order_id,
                "refund_date": refund_date.isoformat(),
                "refund_amount": refund_amount,
                "refund_reason": rng.choice(
                    ["Changed mind", "Skin reaction", "Damaged in transit", "Not as described", "Arrived late"],
                    p=[0.34, 0.24, 0.14, 0.16, 0.12],
                ),
            })
            next_refund_num += 1

        # ---- plan web-session touches for this order (consumed later) ----
        has_ga4_match = rng.random() < 0.88
        touch_plans.append({
            "order_id": order_id,
            "order_date": day,
            "customer_id": cid,
            "order_channel": channel,
            "order_campaign": campaign,
            "device": device,
            "gross_revenue": gross_revenue,
            "has_match": has_ga4_match,
        })

orders_df = pd.DataFrame(orders_rows)
refunds_df = pd.DataFrame(refunds_rows)
customers_df = pd.DataFrame(list(customers.values()))

print(f"Generated {len(orders_df):,} orders, {len(customers_df):,} customers, {len(refunds_df):,} refunds")

# ---------------------------------------------------------------------------
# Ad spend -- backed out from attributed order revenue per (channel,
# campaign, day) using a target ROAS with daily noise, then padded with
# impressions/clicks and an inflated "platform reported" revenue figure.
# ---------------------------------------------------------------------------
orders_df["order_date_dt"] = pd.to_datetime(orders_df["order_date"])
paid_orders = orders_df[orders_df["channel"].isin(PAID_CHANNELS)]
daily_attr_rev = (
    paid_orders.groupby(["order_date_dt", "channel", "campaign"])["gross_revenue"]
    .sum()
    .reset_index()
)

ad_spend_rows = []
CPM_BY_CHANNEL = {"Google Ads": (9, 16), "Meta Ads": (7, 13)}
CTR_BY_CHANNEL = {"Google Ads": (0.025, 0.06), "Meta Ads": (0.008, 0.02)}

# Ensure every (channel,campaign,day) has a spend row even on zero-order
# days (small baseline spend keeps campaigns "always on").
all_days = [d.date() for d in ALL_DATES]
for channel in PAID_CHANNELS:
    for campaign, ad_set in CAMPAIGNS[channel]:
        rev_lookup = daily_attr_rev[
            (daily_attr_rev["channel"] == channel) & (daily_attr_rev["campaign"] == campaign)
        ].set_index("order_date_dt")["gross_revenue"].to_dict()
        target_roas = TARGET_ROAS[(channel, campaign)]
        lo, hi = PLATFORM_INFLATION[channel]
        for day in all_days:
            attr_rev = rev_lookup.get(pd.Timestamp(day), 0.0)
            noise = rng.uniform(0.75, 1.3)
            baseline_spend = {"Google Ads": 45, "Meta Ads": 60}[channel] / len(CAMPAIGNS[channel])
            spend = max(baseline_spend * noise, (attr_rev / target_roas) * noise) if target_roas > 0 else baseline_spend
            spend = round(spend, 2)

            cpm_lo, cpm_hi = CPM_BY_CHANNEL[channel]
            ctr_lo, ctr_hi = CTR_BY_CHANNEL[channel]
            cpm = rng.uniform(cpm_lo, cpm_hi)
            impressions = int(max(50, (spend / cpm) * 1000))
            ctr = rng.uniform(ctr_lo, ctr_hi)
            clicks = int(max(1, impressions * ctr))

            platform_revenue = round(attr_rev * rng.uniform(lo, hi), 2) if attr_rev > 0 else round(spend * rng.uniform(0.3, 1.1), 2)
            platform_conversions = max(0, int(round(platform_revenue / (PRODUCT_LOOKUP["SKU005"]["unit_price"]))))

            ad_spend_rows.append({
                "date": day.isoformat(),
                "channel": channel,
                "campaign": campaign,
                "ad_set": ad_set,
                "product_focus": rng.choice(PRODUCT_IDS, p=PRODUCT_W),
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "platform_reported_revenue": platform_revenue,
                "platform_reported_conversions": platform_conversions,
            })

ad_spend_df = pd.DataFrame(ad_spend_rows)
print(f"Generated {len(ad_spend_df):,} ad_spend rows, total spend ${ad_spend_df['spend'].sum():,.0f}")

# ---------------------------------------------------------------------------
# Web sessions -- purchase-journey touches for matched orders, plus a pool
# of non-converting browse sessions for funnel/CVR realism. Injects the
# tracking-quality issues the Attribution & Tracking Health page analyzes.
# ---------------------------------------------------------------------------
PATH_CHANNEL_POOL = ["Organic Search", "Meta Ads", "Google Ads", "Organic Social", "Direct", "Email/SMS"]
PATH_CHANNEL_W = np.array([0.22, 0.20, 0.16, 0.14, 0.16, 0.12])
PATH_CHANNEL_W = PATH_CHANNEL_W / PATH_CHANNEL_W.sum()

session_rows = []
next_session_num = 1

MISSING_UTM_CHANNELS = {"Meta Ads": 0.22, "Organic Social": 0.30, "Google Ads": 0.08, "Email/SMS": 0.05}


def _utm_fields(channel: str, campaign: str) -> dict:
    medium_map = {
        "Google Ads": "cpc", "Meta Ads": "paid_social", "Organic Search": "organic",
        "Email/SMS": "email", "Direct": "(none)", "Organic Social": "social", "Unattributed": "(not set)",
    }
    medium = medium_map.get(channel, "(not set)")
    missing_p = MISSING_UTM_CHANNELS.get(channel, 0.0)
    if channel in ("Organic Search", "Direct", "Unattributed"):
        return {"utm_source": None, "utm_medium": medium, "utm_campaign": None}
    if rng.random() < missing_p:
        return {"utm_source": channel.lower().replace(" ", "_"), "utm_medium": medium, "utm_campaign": None}
    return {"utm_source": channel.lower().replace(" ", "_"), "utm_medium": medium, "utm_campaign": campaign}


for plan in touch_plans:
    order_date = plan["order_date"]
    device = plan["device"]

    if plan["has_match"]:
        n_touches = int(rng.choice([1, 2, 3, 4], p=[0.42, 0.30, 0.18, 0.10]))
        touch_channels = []
        for t in range(n_touches - 1):
            touch_channels.append(str(rng.choice(PATH_CHANNEL_POOL, p=PATH_CHANNEL_W)))
        # Last touch mirrors the order's channel most of the time (matches
        # what the order system recorded); sometimes it doesn't, which is
        # exactly the kind of last-click vs. order-system mismatch a real
        # GA4 vs. Shopify reconciliation turns up.
        last_matches = rng.random() < 0.78
        last_channel = plan["order_channel"] if last_matches else str(rng.choice(PATH_CHANNEL_POOL, p=PATH_CHANNEL_W))
        touch_channels.append(last_channel)

        for i, ch in enumerate(touch_channels):
            is_last = i == len(touch_channels) - 1
            campaign = plan["order_campaign"] if (is_last and ch == plan["order_channel"]) else _campaign_for(ch)[0]
            days_before = 0 if is_last else int(rng.integers(1, 12))
            sdate = order_date - dt.timedelta(days=days_before)
            utm = _utm_fields(ch, campaign)
            row = {
                "session_id": _id("SESS", next_session_num, 7),
                "session_date": sdate.isoformat(),
                "journey_id": plan["order_id"],
                "customer_id": plan["customer_id"],
                "source": ch,
                "medium": utm["utm_medium"],
                "campaign": campaign,
                "utm_source": utm["utm_source"],
                "utm_medium": utm["utm_medium"],
                "utm_campaign": utm["utm_campaign"],
                "device": device,
                "landing_page": str(rng.choice(LANDING_PAGES)),
                "touch_position": i + 1,
                "touch_count": len(touch_channels),
                "viewed_product": True,
                "added_to_cart": True if is_last else bool(rng.random() < 0.55),
                "began_checkout": True if is_last else bool(rng.random() < 0.25),
                "is_purchase": bool(is_last),
                "transaction_id": plan["order_id"] if is_last else None,
                "revenue_ga4": None,
            }
            if is_last:
                mismatch = rng.random() < 0.16
                row["revenue_ga4"] = round(plan["gross_revenue"] * rng.uniform(0.85, 0.97), 2) if mismatch else plan["gross_revenue"]
            next_session_num += 1
            session_rows.append(row)

            # duplicate purchase-event fire (~2% of purchase sessions)
            if is_last and rng.random() < 0.02:
                dup = dict(row)
                dup["session_id"] = _id("SESS", next_session_num, 7)
                next_session_num += 1
                session_rows.append(dup)
    # else: no session generated at all -> contributes to unattributed revenue

n_touch_sessions = len(session_rows)
print(f"Generated {n_touch_sessions:,} purchase-journey sessions")

# ---- pad with non-converting browse sessions ----
N_BROWSE = int(n_touch_sessions * 2.4)
browse_dates = rng.choice(all_days, size=N_BROWSE)
browse_channels = rng.choice(PATH_CHANNEL_POOL, size=N_BROWSE, p=PATH_CHANNEL_W)

# engagement funnel depth varies by channel (email/organic engage deeper)
DEPTH_W = {
    "Email/SMS": [0.10, 0.30, 0.35, 0.25],
    "Organic Search": [0.20, 0.35, 0.30, 0.15],
    "Direct": [0.22, 0.33, 0.30, 0.15],
    "Meta Ads": [0.45, 0.32, 0.16, 0.07],
    "Google Ads": [0.30, 0.35, 0.22, 0.13],
    "Organic Social": [0.50, 0.30, 0.14, 0.06],
}

for i in range(N_BROWSE):
    ch = str(browse_channels[i])
    sdate = pd.Timestamp(browse_dates[i]).date()
    depth_p = DEPTH_W.get(ch, [0.35, 0.32, 0.22, 0.11])
    depth = rng.choice(["bounce", "viewed", "cart", "checkout"], p=depth_p)
    campaign = _campaign_for(ch)[0]
    utm = _utm_fields(ch, campaign)
    session_rows.append({
        "session_id": _id("SESS", next_session_num, 7),
        "session_date": sdate.isoformat(),
        "journey_id": None,
        "customer_id": None,
        "source": ch,
        "medium": utm["utm_medium"],
        "campaign": campaign,
        "utm_source": utm["utm_source"],
        "utm_medium": utm["utm_medium"],
        "utm_campaign": utm["utm_campaign"],
        "device": str(rng.choice(DEVICES, p=DEVICE_W)),
        "landing_page": str(rng.choice(LANDING_PAGES)),
        "touch_position": 1,
        "touch_count": 1,
        "viewed_product": depth != "bounce",
        "added_to_cart": depth in ("cart", "checkout"),
        "began_checkout": depth == "checkout",
        "is_purchase": False,
        "transaction_id": None,
        "revenue_ga4": None,
    })
    next_session_num += 1

web_sessions_df = pd.DataFrame(session_rows)
print(f"Total web_sessions rows: {len(web_sessions_df):,}")

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------
orders_df = orders_df.drop(columns=["order_date_dt"])

products_df.to_csv(f"{OUT_DIR}/products.csv", index=False)
customers_df.to_csv(f"{OUT_DIR}/customers.csv", index=False)
orders_df.to_csv(f"{OUT_DIR}/orders.csv", index=False)
refunds_df.to_csv(f"{OUT_DIR}/refunds.csv", index=False)
ad_spend_df.to_csv(f"{OUT_DIR}/ad_spend.csv", index=False)
web_sessions_df.to_csv(f"{OUT_DIR}/web_sessions.csv", index=False)

print("\nDone. Files written to", OUT_DIR)
for fname in ["products.csv", "customers.csv", "orders.csv", "refunds.csv", "ad_spend.csv", "web_sessions.csv"]:
    import os
    path = f"{OUT_DIR}/{fname}"
    print(f"  {fname:20s} {os.path.getsize(path)/1024:8.1f} KB")
