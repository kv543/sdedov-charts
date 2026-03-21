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
PIE_COLORS_ROOMS = ["#496970", "#64929C", "#689CAB", "#82C2D2", "#61C0CC"]
PIE_COLORS_PRICE = ["#496970", "#64929C", "#82C2D2", "#61C0CC"]
ROOMS_ORDER     = ["2 חדרים", "3 חדרים", "4 חדרים", "5 חדרים", "6+"]  # לגרף עוגה
ROOMS_BAR_ORDER = ["2 חדרים", "3 חדרים", "4 חדרים", "5 חדרים"]         # לגרפי עמודות

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
    elif r <= 5.5: return "5 חדרים"
    else:          return "6+"


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

    # פילטור עסקאות אופציה — על בסיס עמודת "סוג עסקה" בלבד
    # (שימוש ב-str.contains כדי לתפוס גם "עסקת אופציה", רווחים נוספים וכו')
    is_option = df_all["סוג עסקה"].astype(str).str.contains("אופציה", na=False, case=False)
    df        = df_all[~is_option].copy()

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

    # DataFrames נפרדים לכל מדד — ממוצע מחושב רק מערכים קיימים
    df_price = df.dropna(subset=["price"])
    df_sqm   = df.dropna(subset=["sqm"])
    df_ppm   = df.dropna(subset=["ppm"])
    df_valid = df.dropna(subset=["price", "sqm", "ppm"])  # לטבלת עסקאות בלבד

    # ── 1. KPI ─────────────────────────────────────────────
    def avg_price_rooms(n):
        label = f"{n} חדרים"
        sub   = df_price[df_price["rooms_label"] == label]["price"]
        if len(sub) == 0:
            return 0
        return round(safe_float(sub.mean()) / 1e6, 2)

    kpi = {
        "avg_ppm":            round(safe_float(df_ppm["ppm"].mean())),
        "avg_price":          round(safe_float(df_price["price"].mean())),
        "avg_sqm":            round(safe_float(df_sqm["sqm"].mean()), 1),
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

    monthly_ppm = (df_ppm.groupby("ym")
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
    # התפלגות חדרים — מספיק שיש תגית חדרים תקינה (לא נדרש מחיר/שטח)
    df_rooms_valid = df[df["rooms_label"].notna()]
    rooms_counts = [int(len(df_rooms_valid[df_rooms_valid["rooms_label"] == l])) for l in ROOMS_ORDER]

    # התפלגות מחיר — רק שורות עם מחיר תקין
    price_breaks = [0, 4e6, 7e6, 10e6, float("inf")]
    price_labels = ["עד 4 מ' ₪", "4-7 מ' ₪", "7-10 מ' ₪", "מעל 10 מ' ₪"]
    price_counts = [
        int(((df_price["price"] >= price_breaks[i]) & (df_price["price"] < price_breaks[i+1])).sum())
        for i in range(4)
    ]

    pie = {
        "rooms": {
            "title":    "התפלגות מכירות לפי מספר חדרים",
            "subtitle": "ללא עסקאות אופציה",
            "labels":   ROOMS_ORDER,
            "data":     rooms_counts,
            "colors":   PIE_COLORS_ROOMS
        },
        "price": {
            "title":    "התפלגות מכירות לפי עלות דירה",
            "subtitle": "ללא עסקאות אופציה",
            "labels":   price_labels,
            "data":     price_counts,
            "colors":   PIE_COLORS_PRICE
        }
    }

    # ── 4. גרף עמודות — חדרים ─────────────────────────────
    # כל מדד מחושב מהסט הרלוונטי שלו בלבד (ללא 6+)
    by_rooms_price = (df_price[df_price["rooms_label"].isin(ROOMS_BAR_ORDER)]
                      .groupby("rooms_label").agg(avg_price=("price", "mean"))
                      .reindex(ROOMS_BAR_ORDER))
    by_rooms_sqm   = (df_sqm[df_sqm["rooms_label"].isin(ROOMS_BAR_ORDER)]
                      .groupby("rooms_label").agg(avg_sqm=("sqm", "mean"))
                      .reindex(ROOMS_BAR_ORDER))
    by_rooms_ppm   = (df_ppm[df_ppm["rooms_label"].isin(ROOMS_BAR_ORDER)]
                      .groupby("rooms_label").agg(avg_ppm=("ppm", "mean"))
                      .reindex(ROOMS_BAR_ORDER))

    prices_m = [round(safe_float(v) / 1e6, 2) for v in by_rooms_price["avg_price"]]
    sizes    = [round(safe_float(v), 1)        for v in by_rooms_sqm["avg_sqm"]]
    ppms     = [round(safe_float(v))            for v in by_rooms_ppm["avg_ppm"]]

    rooms_charts = {
        "price": {
            "title":       "מחיר דירה ממוצע לפי מס' חדרים",
            "subtitle":    'במיליוני ש"ח',
            "labels":      ROOMS_BAR_ORDER,
            "data":        prices_m,
            "color":       "#61C0CC",
            "tooltipType": "price",
            "yMin":        0,
            "yMax":        round(max(p for p in prices_m if p > 0) * 1.3) if any(p > 0 for p in prices_m) else 10
        },
        "size": {
            "title":       "שטח ממוצע לפי מס' חדרים",
            "subtitle":    'במטרים רבועים',
            "labels":      ROOMS_BAR_ORDER,
            "data":        sizes,
            "color":       "#496970",
            "tooltipType": "size",
            "yMin":        0,
            "yMax":        round(max(s for s in sizes if s > 0) * 1.3) if any(s > 0 for s in sizes) else 200
        },
        "pricePerSqm": {
            "title":       'מחיר ממוצע למ"ר לפי מס\' חדרים',
            "subtitle":    'בשקלים',
            "labels":      ROOMS_BAR_ORDER,
            "data":        ppms,
            "color":       "#7dcdd7",
            "tooltipType": "pricePerSqm",
            "yMin":        20000,
            "yMax":        100000
        }
    }

    # ── 5. מחירי קצה — רבעוני ─────────────────────────────
    quarters_sorted  = sorted(df_price["yq"].unique())
    q_labels         = [quarter_label(y, q) for y, q in quarters_sorted]

    df_cheap     = df_price[df_price["price"] < 4e6]
    df_expensive = df_price[df_price["price"] > 10e6]

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

    top_exp   = df_price.nlargest(10, "price")
    top_cheap = df_price.nsmallest(10, "price")

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


# ── פונקציה לגרף עלות קרקע ──────────────────────────────────

def generate_land_chart_data(excel_path) -> dict:
    """
    מייצר נתונים לגרף עלות קרקע ליחידת דיור.

    מבנה אקסל מצופה (גמיש):
      - עמודת תאריך  (תאריך / date / ...)
      - עמודת מחיר ליח"ד בש"ח (מחיר / price / ערך / הצעה / ...)
      - שורה אחת או יותר לכל מכרז — מקובצות לפי תאריך
    """
    df = pd.read_excel(excel_path)

    # ── זיהוי עמודת תאריך ───────────────────────────────────
    date_col = None
    for c in df.columns:
        if any(k in str(c) for k in ['תאריך', 'date', 'Date', 'שנה']):
            date_col = c
            break
    if date_col is None:
        date_col = df.columns[0]

    # ── זיהוי עמודת מחיר ────────────────────────────────────
    price_col = None
    price_kw  = ['מחיר', 'price', 'Price', 'ערך', 'שווי', 'הצעה', 'תמורה']
    for c in df.columns:
        if c == date_col:
            continue
        if any(k in str(c) for k in price_kw):
            price_col = c
            break
    if price_col is None:
        # fallback — עמודה מספרית ראשונה שאינה התאריך
        for c in df.columns:
            if c != date_col and pd.api.types.is_numeric_dtype(df[c]):
                price_col = c
                break
    if price_col is None:
        raise ValueError(f"לא נמצאה עמודת מחיר. עמודות: {list(df.columns)}")

    df["_date"]  = pd.to_datetime(df[date_col],  errors="coerce", dayfirst=True)
    df["_price"] = pd.to_numeric(df[price_col],  errors="coerce")
    df = df.dropna(subset=["_date", "_price"]).sort_values("_date")

    if df.empty:
        raise ValueError("לא נמצאו שורות תקינות בקובץ")

    # המרה למיליוני ₪ אם הערכים בש"ח
    if df["_price"].median() > 100_000:
        df["_price"] = df["_price"] / 1e6

    # ── קיבוץ לפי תאריך ─────────────────────────────────────
    grouped = (df.groupby("_date")
               .agg(avg=("_price","mean"), mn=("_price","min"), mx=("_price","max"))
               .reset_index()
               .sort_values("_date"))

    labels  = [f"{MONTHS_HE[d.month]} {d.year}" for d in grouped["_date"]]
    avgs    = [round(safe_float(v), 2) for v in grouped["avg"]]
    mins    = [round(safe_float(v), 2) for v in grouped["mn"]]
    maxs    = [round(safe_float(v), 2) for v in grouped["mx"]]

    all_vals = [v for v in avgs + mins + maxs if v > 0]
    y_min = round(min(all_vals) * 0.85 * 10) / 10 if all_vals else 0
    y_max = round(max(all_vals) * 1.15 * 10) / 10 if all_vals else 5

    return {
        "title":    "עלות קרקע ליחידת דיור",
        "subtitle": 'התפתחות מחיר הקרקע הממוצע ליח"ד במכרזי שדה דב לפי תאריך סגירת מכרז',
        "note":     "* הטווח מייצג את הפיזור בין הצעות הזוכים בכל מכרז",
        "labels":   labels,
        "avg":      avgs,
        "min":      mins,
        "max":      maxs,
        "yMin":     y_min,
        "yMax":     y_max,
    }
