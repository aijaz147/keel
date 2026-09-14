# Looker Studio build

A companion to the main app: the same order, ad-spend, and session data, exported as flat tables and rebuilt as a Looker Studio report instead of a Streamlit one.

Covers Executive Overview, Paid Media Performance, Product & Profitability, and Customer & Retention. Attribution & Tracking Health stays in the Streamlit app — the multi-touch attribution switching needs a query engine behind it, not a flat file.

## Regenerating the data

```bash
python looker_studio/export_looker_data.py
```

Writes six CSVs into `looker_studio/data/`, using the same functions in `src/metrics.py` the main app runs on, so the numbers always agree with each other.

| File | Grain |
|---|---|
| `channel_daily.csv` | date × channel × campaign |
| `orders_detail.csv` | order line |
| `product_summary.csv` | SKU |
| `cohort_retention.csv` | cohort month × month index |
| `new_vs_returning_monthly.csv` | month × segment |
| `customer_summary.csv` | single row, headline stats |

The full build walkthrough — data source setup, every calculated-field formula, and a chart-by-chart spec for each page — is a separate reference doc kept outside the repo.
