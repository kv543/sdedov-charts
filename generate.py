#!/usr/bin/env python3
"""
מחולל JSON לגרפי שדה דב
━━━━━━━━━━━━━━━━━━━━━━━
שימוש: python generate_charts_json.py [קובץ_אקסל.xlsx]

הסקריפט קורא קובץ אקסל עם נתוני עסקאות, מסנן עסקאות אופציה,
ומייצר את כל קבצי ה-JSON הנדרשים לגרפים באתר.

קבצי הפלט (תיקייה json_output/):
  shadeh-dov-kpi.json            ← כרטיסי KPI
  shadeh-dov-charts.json         ← גרף חודשי (כמות / מצטבר / מחיר למ"ר)
  shadeh-dov-pie-charts.json     ← גרף עוגה (חדרים / מחיר)
  shadeh-dov-rooms-charts.json   ← גרף עמודות לפי חדרים
  shadeh-dov-price-ranges.json   ← גרף מחירי קצה (זול / יקר לרבעון)
  shadeh-dov-transactions.json   ← טבלת עסקאות (10 יקרות / 10 זולות)

לאחר הרצה: העלה את כל קבצי ה-JSON לתיקייה:
  https://sdedov.co.il/wp-content/uploads/data/
"""

import json
import os
import sys
import pandas as pd
import numpy as np

# ══════════════════════════════════════════════════════════════
# הגדרות — שנה כאן בלבד
# ══════════════════════════════════════════════════════════════

EXCEL_FILE   = ""
OUTPUT_DIR   = "data"

# כרטיס פרויקטים (לא נגזר מהעסקאות — עדכן ידנית)
PROJECTS_COUNT = 7
PROJECTS_URL   = "https://sdedov.co.il/projects/"

# צבעים לגרף עוגה
PIE_COLORS = ["#2d6b75", "#496970", "#61C0CC", "#7dcdd7"]

# ══════════════════════════════════════════════════════════════
# עזר
# ══════════════════════════════════════════════════════════════

MONTHS_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ",    4: "אפריל",
    5: "מאי",   6: "יוני",   7: "יולי",   8: "אוגוסט",
    9: "ספטמבר",10: "אוקטובר",11: "נובמבר",12: "דצמבר"
}

def month_label(year, month):
    return f"{MONTHS_HE[int(month)]} {int(year)}"

def quarter_label(year, quarter):
    return f"רבעון {quarter} {int(year)}"

def save_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓  {filename}")

def safe_int(v):
    try:
        iv = int(v)
        return iv if iv == v else v
    except Exception:
        return v

def format_date_he(row):
    return f"{int(row['יום'])} ב{MONTHS_HE[int(row['חודש'])]} {int(row['שנה'])}"

def rooms_group(r):
    if   r <= 0:   return None
    elif r <= 2.5: return "2 חדרים"
    elif r <= 3.5: return "3 חדרים"
    elif r <= 4.5: return "4 חדרים"
    else:          return "5 חדרים"

# ══════════════════════════════════════════════════════════════
# טעינה
# ══════════════════════════════════════════════════════════════

excel_path = sys.argv[1] if len(sys.argv) > 1 else EXCEL_FILE
print(f"\n📂  קורא: {excel_path}")

df_all = pd.read_excel(excel_path)
df = df_all[df_all["סוג עסקה"] != "אופציה"].copy()

# עיבוד כלל העסקאות (כולל אופציה) — לכמות חודשית ו-KPI
for src in [df_all, df]:
    src["price"]      = pd.to_numeric(src['תמורה מוצהרת בש"ח'], errors="coerce")
    src["ppm"]        = pd.to_numeric(src["מחיר למ״ר"],         errors="coerce")
    src["sqm"]        = pd.to_numeric(src["שטח"],                errors="coerce")
    src["year"]       = src["שנה"].astype(int)
    src["month"]      = src["חודש"].astype(int)
    src["rooms_raw"]  = pd.to_numeric(src["חדרים"], errors="coerce").fillna(0)
    src["build_year"] = pd.to_numeric(src["שנת בניה"], errors="coerce")
    src["rooms_label"]= src["rooms_raw"].apply(rooms_group)
    src["quarter"]    = ((src["month"] - 1) // 3 + 1).astype(int)
    src["ym"]         = list(zip(src["year"], src["month"]))
    src["yq"]         = list(zip(src["year"], src["quarter"]))

df_valid     = df.dropna(subset=["price", "sqm", "ppm"])      # ללא אופציה — לרוב הגרפים
df_all_valid = df_all.dropna(subset=["price", "sqm", "ppm"])  # כולל אופציה — לכמות חודשית

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"📊  סה\"כ עסקאות (כולל אופציה): {len(df_all)}")
print(f"📊  עסקאות ללא אופציה:          {len(df)}\n")

ROOMS_ORDER = ["2 חדרים", "3 חדרים", "4 חדרים", "5 חדרים"]

# ══════════════════════════════════════════════════════════════
# 1. KPI
# ══════════════════════════════════════════════════════════════

def avg_price_rooms(n):
    label = f"{n} חדרים"
    sub   = df_valid[df_valid["rooms_label"] == label]["price"]
    return round(sub.mean() / 1e6, 2) if len(sub) else 0

kpi = {
    "avg_ppm":            round(df_valid["ppm"].mean()),
    "avg_price":          round(df_valid["price"].mean()),
    "avg_sqm":            round(df_valid["sqm"].mean(), 1),
    "total_transactions": int(len(df_all)),  # כולל עסקאות אופציה
    "avg_price_3rooms":   avg_price_rooms(3),
    "avg_price_4rooms":   avg_price_rooms(4),
    "projects_count":     PROJECTS_COUNT,
    "projects_url":       PROJECTS_URL
}
save_json("shadeh-dov-kpi.json", kpi)

# ══════════════════════════════════════════════════════════════
# 2. גרף חודשי — כמות / מצטבר / מחיר למ"ר
# ══════════════════════════════════════════════════════════════

# כמות ומצטבר — כולל עסקאות אופציה (ספירה לפי שורות, ללא סינון NaN)
monthly_all = (df_all.groupby("ym")
               .agg(count=("price", "count"))
               .reset_index()
               .sort_values("ym"))

# מחיר למ"ר — ללא עסקאות אופציה
monthly_ppm = (df_valid.groupby("ym")
               .agg(avg_ppm=("ppm", "mean"))
               .reset_index()
               .sort_values("ym"))

# ציר זמן אחיד לפי כלל העסקאות
labels     = [month_label(y, m) for y, m in monthly_all["ym"]]
counts     = [int(v) for v in monthly_all["count"]]
cumulative = [int(v) for v in monthly_all["count"].cumsum()]

# מחיר למ"ר ממולא לפי אותו ציר זמן
ppm_dict  = {tuple(row["ym"]): round(float(row["avg_ppm"])) for _, row in monthly_ppm.iterrows()}
avg_ppm_m = [ppm_dict.get(ym, 0) for ym in monthly_all["ym"]]

y_ppm_max = round(max(avg_ppm_m) * 1.25 / 5000) * 5000

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
        "yMin":        round(min(avg_ppm_m) * 0.85 / 5000) * 5000,
        "yMax":        y_ppm_max
    }
}
save_json("shadeh-dov-charts.json", charts)

# ══════════════════════════════════════════════════════════════
# 3. גרף עוגה — חדרים / טווח מחיר
# ══════════════════════════════════════════════════════════════

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
save_json("shadeh-dov-pie-charts.json", pie)

# ══════════════════════════════════════════════════════════════
# 4. גרף עמודות — לפי חדרים
# ══════════════════════════════════════════════════════════════

df_r = df_valid[df_valid["rooms_label"].notna()]
by_rooms = (df_r.groupby("rooms_label")
            .agg(avg_price=("price","mean"), avg_sqm=("sqm","mean"), avg_ppm=("ppm","mean"))
            .reindex(ROOMS_ORDER))

prices_m = [round(float(v)/1e6, 2) for v in by_rooms["avg_price"]]
sizes    = [round(float(v), 1)      for v in by_rooms["avg_sqm"]]
ppms     = [round(float(v))         for v in by_rooms["avg_ppm"]]

rooms_charts = {
    "price": {
        "title":       "מחיר דירה ממוצע לפי מס' חדרים (ללא עסקאות אופציה)",
        "subtitle":    'במיליוני ש"ח',
        "labels":      ROOMS_ORDER,
        "data":        prices_m,
        "color":       "#61C0CC",
        "tooltipType": "price",
        "yMin":        0,
        "yMax":        round(max(prices_m) * 1.3)
    },
    "size": {
        "title":       "שטח ממוצע לפי מס' חדרים (ללא עסקאות אופציה)",
        "subtitle":    'במטרים רבועים',
        "labels":      ROOMS_ORDER,
        "data":        sizes,
        "color":       "#496970",
        "tooltipType": "size",
        "yMin":        0,
        "yMax":        round(max(sizes) * 1.3)
    },
    "pricePerSqm": {
        "title":       'מחיר ממוצע למ"ר לפי מס\' חדרים (ללא עסקאות אופציה)',
        "subtitle":    'בשקלים',
        "labels":      ROOMS_ORDER,
        "data":        ppms,
        "color":       "#7dcdd7",
        "tooltipType": "pricePerSqm",
        "yMin":        round(min(ppms) * 0.8 / 10000) * 10000,
        "yMax":        round(max(ppms) * 1.2 / 10000) * 10000
    }
}
save_json("shadeh-dov-rooms-charts.json", rooms_charts)

# ══════════════════════════════════════════════════════════════
# 5. גרף מחירי קצה — רבעוני
# ══════════════════════════════════════════════════════════════

quarters_sorted = sorted(df_valid["yq"].unique())
q_labels        = [quarter_label(y, q) for y, q in quarters_sorted]

df_cheap     = df_valid[df_valid["price"] < 4e6]
df_expensive = df_valid[df_valid["price"] > 10e6]

cheap_counts     = [int(len(df_cheap[df_cheap["yq"]     == yq])) for yq in quarters_sorted]
expensive_counts = [int(len(df_expensive[df_expensive["yq"] == yq])) for yq in quarters_sorted]

price_ranges = {
    "cheap": {
        "labels": q_labels,
        "data":   cheap_counts,
        "color":  "#61C0CC"
    },
    "expensive": {
        "labels": q_labels,
        "data":   expensive_counts,
        "color":  "#496970"
    }
}
save_json("shadeh-dov-price-ranges.json", price_ranges)

# ══════════════════════════════════════════════════════════════
# 6. טבלת עסקאות — 10 יקרות / 10 זולות
# ══════════════════════════════════════════════════════════════

def make_row(row):
    return {
        "date":       format_date_he(row),
        "complex":    "שדה דב",
        "price":      round(float(row["price"])),
        "sqm":        round(float(row["sqm"])),
        "rooms":      safe_int(row["rooms_raw"]),
        "build_year": safe_int(row["build_year"]) if pd.notna(row["build_year"]) else "",
        "ppm":        round(float(row["ppm"]))
    }

top_exp   = df_valid.nlargest(10, "price")
top_cheap = df_valid.nsmallest(10, "price")

transactions = {
    "expensive": [make_row(r) for _, r in top_exp.iterrows()],
    "cheap":     [make_row(r) for _, r in top_cheap.iterrows()]
}
save_json("shadeh-dov-transactions.json", transactions)

# ══════════════════════════════════════════════════════════════
# סיכום
# ══════════════════════════════════════════════════════════════

print(f"""
✅  הושלם בהצלחה!
    עסקאות שעובדו (ללא אופציה): {len(df)}
    טווח תאריכים: {month_label(df['year'].min(), df.loc[df['year']==df['year'].min(),'month'].min())} – {month_label(df['year'].max(), df.loc[df['year']==df['year'].max(),'month'].max())}
    קבצים נשמרו ב: {os.path.abspath(OUTPUT_DIR)}/

📤  כעת העלה את כל הקבצים מתיקייה json_output/ לנתיב:
    wp-content/uploads/data/
""")
