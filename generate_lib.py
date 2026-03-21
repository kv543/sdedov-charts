"""
generate_lib.py — ספריית עיבוד נתוני שדה דב
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
פונקציה אחת ראשית: generate_all_data(excel_path, ...)
מחזירה dict עם כל הנתונים הנדרשים לגרפים.
"""

import math
import pandas as pd
import numpy as np

# ── קבועים ──────────────────────────────────────────────────
MONTHS_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ",     4: "אפריל",
    5: "מאי",   6: "יוני",   7: "יולי",    8: "אוגוסט",
    9: "ספטמבר",10: "אוקטובר",11: "נובמבר",12: "דצמבר"
}
PIE_COLORS  = ["#2d6b75", "#496970", "#61C0CC", "#7dcdd7"]
ROOMS_ORDER = ["2 חדרים", "3 חדרים", "4 חדרים", "5 חדרים"]

# ── עזר ────────────────────────────────────────────────────

def month_label(year, month):
    return f"{MONTHS_HE[int(month)]} {int(year)}"

def quarter_label(year, quarter):
    return f"רבעון {quarter} {int(year)}"

def safe_int(v):
    try:
        iv = int(v)
        return iv if iv == v else float(v)
    except Exception:
        return str(v) if v is not None else ""

def safe_float(v, default=0.0):
    """המרה בטוחה ל-float עם טיפול ב-NaN"""
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return default

def format_date_he(row):
    return f"{int(row['יום'])} ב{MONTHS_HE[int(row['חודש'])]} {int(row['שנה'])}"

def rooms_group(r):
    if   r <= 0:   return None
    elif r <= 2.5: return "2 חדרים"
    elif r <= 3.5: return "3 חדרים"
    elif r <= 4.5: return "4 חדרים"
    else:          return "5 חדרים"


# ── פונקציה ראשית ───────────────────────────────────────────

def generate_all_data(
    excel_path,
    projects_count: int = 7,
    projects_url:   str = "https://sdedov.co.il/projects/"
) -> dict:
    """
    קורא קובץ Excel ומחזיר dict עם כל הנתונים לגרפים.

    מבנה הפלט:
    {
      kpi, charts, pie, rooms_charts, price_ranges, transactions, meta
    }
    """

    # ── טעינה ──────────────────────────────────────────────
    df_all = pd.read_excel(excel_path)
    df     = df_all[df_all["סוג עסקה"] != "אופציה"].copy()

    # עיבוד עמודות על שני ה-DataFrames
    for src in [df_all, df]:
        src["price"]       = pd.to_numeric(src['תמורה מוצהרת בש"ח'], errors="coerce")
        src["ppm"]         = pd.to_numeric(src["מחיר למ״ר"],          errors="coerce")
        src["sqm"]         = pd.to_numeric(src["שטח"],                 errors="coerce")
        src["year"]        = src["שנה"].astype(int)
        src["month"]       = src["חודש"].astype(int)
        src["rooms_raw"]   = pd.to_numeric(src["חדרים"], errors="coerce").fillna(0)
        src["build_year"]  = pd.to_numeric(src["שנת בניה"], errors="coerce")
        src["rooms_label"] = src["rooms_raw"].apply(rooms_group)
        src["quarter"]     = ((src["month"] - 1) // 3 + 1).astype(int)
        src["ym"]          = list(zip(src["year"], src["month"]))
        src["yq"]          = list(zip(src["year"], src["quarter"]))

    df_valid = df.dropna(subset=["price", "sqm", "ppm"])

    # ── 1. KPI ─────────────────────────────────────────────
    def avg_price_rooms(n):
        label = f"{n} חדרים"
        sub   = df_valid[df_valid["rooms_label"] == label]["price"]
        if len(sub) == 0:
            return 0
        return round(safe_float(sub.mean()) / 1e6, 2)

    kpi = {
        "avg_ppm":            round(safe_float(df_valid["ppm"].mean())),
        "avg_price":          round(safe_float(df_valid["price"].mean())),
        "avg_sqm":            round(safe_float(df_valid["sqm"].mean()), 1),
        "total_transactions": int(len(df_all)),
        "avg_price_3rooms":   avg_price_rooms(3),
        "avg_price_4rooms":   avg_price_rooms(4),
        "projects_count":     int(projects_count),
        "projects_url":       projects_url
    }

    # ── 2. גרף חודשי ───────────────────────────────────────
    monthly_all = (df_all.groupby("ym")
                   .agg(count=("price", "count"))
                   .reset_index()
                   .sort_values("ym"))

    monthly_ppm = (df_valid.groupby("ym")
                   .agg(avg_ppm=("ppm", "mean"))
                   .reset_index()
                   .sort_values("ym"))

    labels     = [month_label(y, m) for y, m in monthly_all["ym"]]
    counts     = [int(v) for v in monthly_all["count"]]
    cumulative = [int(v) for v in monthly_all["count"].cumsum()]

    ppm_dict  = {tuple(row["ym"]): round(safe_float(row["avg_ppm"]))
                 for _, row in monthly_ppm.iterrows()}
    avg_ppm_m = [ppm_dict.get(ym, 0) for ym in monthly_all["ym"]]

    valid_ppms = [v for v in avg_ppm_m if v > 0]
    y_ppm_min  = round(min(valid_ppms) * 0.85 / 5000) * 5000 if valid_ppms else 0
    y_ppm_max  = round(max(valid_ppms) * 1.25 / 5000) * 5000 if valid_ppms else 100000

    charts = {
        "count": {
            "title":       "כמות דירות שנמכרו בשדה דב לפי חודשים",
            "labels":      labels,
            "data":        counts,
            "color":       "#496970",
            "tooltipType": "count"
        },
        "cumulative": {
            "title":       "כמות עסקאות מצטברת בשדה דב",
            "labels":      labels,
            "data":        cumulative,
            "color":       "#61C0CC",
            "tooltipType": "cumulative"
        },
        "price": {
            "title":       'מחיר ממוצע למ"ר בשדה דב לפי חודשים',
            "labels":      labels,
            "data":        avg_ppm_m,
            "color":       "#7dcdd7",
            "tooltipType": "price",
            "yMin":        y_ppm_min,
            "yMax":        y_ppm_max
        }
    }

    # ── 3. גרף עוגה ────────────────────────────────────────
    rooms_counts = [int(len(df_valid[df_valid["rooms_label"] == l])) for l in ROOMS_ORDER]

    price_breaks = [0, 4e6, 7e6, 10e6, float("inf")]
    price_labels = ["עד 4 מ'", "4–7 מ'", "7–10 מ'", "מעל 10 מ'"]
    price_counts = [
        int(((df_valid["price"] >= price_breaks[i]) & (df_valid["price"] < price_breaks[i+1])).sum())
        for i in range(4)
    ]

    pie = {
        "rooms": {
            "title":    "התפלגות מכירות לפי מספר חדרים",
            "subtitle": "ללא עסקאות אופציה",
            "labels":   ROOMS_ORDER,
            "data":     rooms_counts,
            "colors":   PIE_COLORS
        },
        "price": {
            "title":    "התפלגות מכירות לפי טווח מחיר",
            "subtitle": "ללא עסקאות אופציה",
            "labels":   price_labels,
            "data":     price_counts,
            "colors":   PIE_COLORS
        }
    }

    # ── 4. גרף עמודות — חדרים ─────────────────────────────
    df_r     = df_valid[df_valid["rooms_label"].notna()]
    by_rooms = (df_r.groupby("rooms_label")
                .agg(avg_price=("price", "mean"), avg_sqm=("sqm", "mean"), avg_ppm=("ppm", "mean"))
                .reindex(ROOMS_ORDER))

    prices_m = [round(safe_float(v) / 1e6, 2) for v in by_rooms["avg_price"]]
    sizes    = [round(safe_float(v), 1)        for v in by_rooms["avg_sqm"]]
    ppms     = [round(safe_float(v))            for v in by_rooms["avg_ppm"]]

    rooms_charts = {
        "price": {
            "title":       "מחיר דירה ממוצע לפי מס' חדרים",
            "subtitle":    'במיליוני ש"ח',
            "labels":      ROOMS_ORDER,
            "data":        prices_m,
            "color":       "#61C0CC",
            "tooltipType": "price",
            "yMin":        0,
            "yMax":        round(max(p for p in prices_m if p > 0) * 1.3) if any(p > 0 for p in prices_m) else 10
        },
        "size": {
            "title":       "שטח ממוצע לפי מס' חדרים",
            "subtitle":    'במטרים רבועים',
            "labels":      ROOMS_ORDER,
            "data":        sizes,
            "color":       "#496970",
            "tooltipType": "size",
            "yMin":        0,
            "yMax":        round(max(s for s in sizes if s > 0) * 1.3) if any(s > 0 for s in sizes) else 200
        },
        "pricePerSqm": {
            "title":       'מחיר ממוצע למ"ר לפי מס\' חדרים',
            "subtitle":    'בשקלים',
            "labels":      ROOMS_ORDER,
            "data":        ppms,
            "color":       "#7dcdd7",
            "tooltipType": "pricePerSqm",
            "yMin":        round(min(p for p in ppms if p > 0) * 0.8 / 10000) * 10000 if any(p > 0 for p in ppms) else 0,
            "yMax":        round(max(p for p in ppms if p > 0) * 1.2 / 10000) * 10000 if any(p > 0 for p in ppms) else 100000
        }
    }

    # ── 5. מחירי קצה — רבעוני ─────────────────────────────
    quarters_sorted  = sorted(df_valid["yq"].unique())
    q_labels         = [quarter_label(y, q) for y, q in quarters_sorted]

    df_cheap     = df_valid[df_valid["price"] < 4e6]
    df_expensive = df_valid[df_valid["price"] > 10e6]

    cheap_counts     = [int(len(df_cheap[df_cheap["yq"]         == yq])) for yq in quarters_sorted]
    expensive_counts = [int(len(df_expensive[df_expensive["yq"] == yq])) for yq in quarters_sorted]

    price_ranges = {
        "cheap":     {"labels": q_labels, "data": cheap_counts,     "color": "#61C0CC"},
        "expensive": {"labels": q_labels, "data": expensive_counts, "color": "#496970"}
    }

    # ── 6. טבלת עסקאות ────────────────────────────────────
    def make_row(row):
        return {
            "date":       format_date_he(row),
            "complex":    "שדה דב",
            "price":      round(safe_float(row["price"])),
            "sqm":        round(safe_float(row["sqm"])),
            "rooms":      safe_int(row["rooms_raw"]),
            "build_year": safe_int(row["build_year"]) if pd.notna(row["build_year"]) else "",
            "ppm":        round(safe_float(row["ppm"]))
        }

    top_exp   = df_valid.nlargest(10, "price")
    top_cheap = df_valid.nsmallest(10, "price")

    transactions = {
        "expensive": [make_row(r) for _, r in top_exp.iterrows()],
        "cheap":     [make_row(r) for _, r in top_cheap.iterrows()]
    }

    # ── מטא-נתונים ────────────────────────────────────────
    yr_min  = int(df["year"].min())
    mo_min  = int(df.loc[df["year"] == yr_min, "month"].min())
    yr_max  = int(df["year"].max())
    mo_max  = int(df.loc[df["year"] == yr_max, "month"].max())

    meta = {
        "total":      int(len(df_all)),
        "no_option":  int(len(df)),
        "date_range": f"{month_label(yr_min, mo_min)} – {month_label(yr_max, mo_max)}"
    }

    return {
        "kpi":          kpi,
        "charts":       charts,
        "pie":          pie,
        "rooms_charts": rooms_charts,
        "price_ranges": price_ranges,
        "transactions": transactions,
        "meta":         meta
    }
